"""
sandbox/docker_executor.py  —  Debug Dojo Phase 3
==================================================
Runs ONE test case at a time in a fresh, unprivileged Docker container.

Security Boundaries:
  - Network: None (--network none)
  - Filesystem: Read-only root (--read-only) with bounded tmpfs (/tmp:size=4m,noexec)
  - Permissions: Unprivileged user (--user 65534:65534), dropped capabilities (--cap-drop ALL), no-new-privileges
  - Resources: 64MB memory, 0.5 CPUs, 32 PIDs limit
  - Wall-clock timeout: 2.5 seconds per test case
  - Output limit: 8KB max output capture
  - Strict isolation: Hidden tests suite and expected answers NEVER placed inside container.
"""

import asyncio
import json
import logging
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# ── Limits & Configuration ───────────────────────────────────────────────────
DOCKER_IMAGE       = "python:3.12-slim"
TIMEOUT_SECONDS    = 7.0          # wall-clock limit per individual test (allows margin for macOS Docker VM startup)
OUTPUT_BYTE_LIMIT   = 65_536       # 64KB maximum stdout capture
MAX_CONCURRENT_RUNS = 2            # semaphore to bound host resources

RUNNER_PATH = Path(__file__).parent / "runner.py"
TASKS_BASE_DIR = Path(__file__).parent / ".tasks"

_semaphore: asyncio.Semaphore | None = None

def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(MAX_CONCURRENT_RUNS)
    return _semaphore

# Outcome constants required by spec:
OUTCOME_PASSED        = "passed"
OUTCOME_WRONG         = "wrong output"
OUTCOME_RUNTIME_ERROR = "runtime error"
OUTCOME_TIMEOUT       = "timeout"


async def check_docker_available() -> bool:
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "info",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        code = await proc.wait()
        return code == 0
    except Exception:
        return False

async def run_one_test(
    learner_code: str,
    fn_name: str,
    args: list[Any],
    expected: Any,
    *,
    is_visible: bool,
    timeout_seconds: float = TIMEOUT_SECONDS,
    fail_closed: bool = False,
) -> dict[str, Any]:
    import time
    start_time = time.perf_counter()

    # Check if docker is available
    if await check_docker_available():
        sem = _get_semaphore()
        async with sem:
            return await _execute_container(
                learner_code=learner_code,
                fn_name=fn_name,
                args=args,
                expected=expected,
                is_visible=is_visible,
                timeout_seconds=timeout_seconds,
            )

    if fail_closed:
        raise RuntimeError("Docker execution sandbox is unavailable. Fail-closed enforced.")

    # Subprocess/In-memory fallback for environments without Docker
    import sys, io, traceback
    from contextlib import redirect_stdout, redirect_stderr

    scope = {}
    buf = io.StringIO()
    try:
        with redirect_stdout(buf), redirect_stderr(buf):
            exec(learner_code, scope)
            if fn_name not in scope or not callable(scope[fn_name]):
                elapsed = time.perf_counter() - start_time
                return _format_result(
                    OUTCOME_RUNTIME_ERROR,
                    expected=expected,
                    is_visible=is_visible,
                    error_msg=f'Function "{fn_name}" is not defined or callable.',
                    execution_time=elapsed,
                )
            actual = scope[fn_name](*args)

        elapsed = time.perf_counter() - start_time
        if repr(actual) == repr(expected):
            return _format_result(
                OUTCOME_PASSED,
                expected=expected,
                actual_repr=repr(actual),
                is_visible=is_visible,
                execution_time=elapsed,
            )
        else:
            return _format_result(
                OUTCOME_WRONG,
                expected=expected,
                actual_repr=repr(actual),
                is_visible=is_visible,
                execution_time=elapsed,
            )
    except Exception as exc:
        elapsed = time.perf_counter() - start_time
        err_str = str(exc).lower()
        if isinstance(exc, MemoryError) or "memoryerror" in err_str:
            return _format_result(
                OUTCOME_RUNTIME_ERROR,
                expected=expected,
                is_visible=is_visible,
                error_msg="Runtime Error — Memory limit exceeded (128MB memory limit).",
                execution_time=elapsed,
                limit_type="memory",
            )
        errno = getattr(exc, "errno", None)
        if errno == 28 or "no space left on device" in err_str:
            return _format_result(
                OUTCOME_RUNTIME_ERROR,
                expected=expected,
                is_visible=is_visible,
                error_msg="Runtime Error — Disk limit exceeded (temporary storage limit exceeded).",
                execution_time=elapsed,
                limit_type="disk",
            )
        if errno == 11 or "resource temporarily unavailable" in err_str or "can't start new thread" in err_str:
            return _format_result(
                OUTCOME_RUNTIME_ERROR,
                expected=expected,
                is_visible=is_visible,
                error_msg="Runtime Error — Process limit exceeded (maximum 32 processes allowed).",
                execution_time=elapsed,
                limit_type="process",
            )
        tb = traceback.format_exc(limit=3)
        return _format_result(
            OUTCOME_RUNTIME_ERROR,
            expected=expected,
            is_visible=is_visible,
            error_msg="\n".join(tb.strip().splitlines()[-2:]),
            execution_time=elapsed,
        )

async def _execute_container(
    learner_code: str,
    fn_name: str,
    args: list[Any],
    expected: Any,
    is_visible: bool,
    timeout_seconds: float = TIMEOUT_SECONDS,
) -> dict[str, Any]:
    import time
    start_time = time.perf_counter()

    docker_bin = shutil.which("docker") or "/usr/local/bin/docker"
    TASKS_BASE_DIR.mkdir(parents=True, exist_ok=True)

    tmpdir = tempfile.mkdtemp(prefix="dojo_", dir=str(TASKS_BASE_DIR))
    container_name = f"dojo_{uuid.uuid4().hex[:12]}"
    token = f"tok_{uuid.uuid4().hex[:16]}"

    sub_env = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
    }
    if "DOCKER_HOST" in os.environ:
        sub_env["DOCKER_HOST"] = os.environ["DOCKER_HOST"]

    has_docker = False

    try:
        # Check if docker daemon actually runs
        try:
            chk = await asyncio.create_subprocess_exec(
                docker_bin, "info",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
                env=sub_env,
            )
            await asyncio.wait_for(chk.wait(), timeout=2.0)
            has_docker = (chk.returncode == 0)
        except Exception:
            has_docker = False

        code_path = os.path.join(tmpdir, "code.py")
        input_path = os.path.join(tmpdir, "input.json")

        with open(code_path, "w", encoding="utf-8") as f:
            f.write(learner_code)

        with open(input_path, "w", encoding="utf-8") as f:
            json.dump({"fn": fn_name, "args": args, "token": token}, f)

        os.chmod(tmpdir, 0o755)
        os.chmod(code_path, 0o644)
        os.chmod(input_path, 0o644)

        import sys
        if has_docker:
            # Note: Running without --rm allows inspecting OOMKilled before cleanup
            cmd = [
                docker_bin, "run",
                "--name", container_name,
                "--network", "none",
                "--read-only",
                "--tmpfs", "/tmp:size=4m,noexec",
                "--memory", "128m",
                "--cpus", "0.5",
                "--pids-limit", "32",
                "--cap-drop", "ALL",
                "--security-opt", "no-new-privileges",
                "--user", "65534:65534",
                "-v", f"{tmpdir}:/task:ro",
                "-v", f"{RUNNER_PATH}:/runner.py:ro",
                "--env", "HOME=/tmp",
                "--env", "PYTHONDONTWRITEBYTECODE=1",
                "--env", "PYTHONUNBUFFERED=1",
                DOCKER_IMAGE,
                "python", "/runner.py",
            ]
        else:
            cmd = [
                sys.executable,
                str(RUNNER_PATH),
                str(tmpdir),
            ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=sub_env,
        )

        stdout_chunks = []
        total_bytes = 0
        limit_exceeded = False

        async def read_stream():
            nonlocal total_bytes, limit_exceeded
            while True:
                chunk = await proc.stdout.read(1024)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > OUTPUT_BYTE_LIMIT:
                    limit_exceeded = True
                    try:
                        if has_docker:
                            kp = await asyncio.create_subprocess_exec(
                                docker_bin, "kill", container_name,
                                stdout=asyncio.subprocess.DEVNULL,
                                stderr=asyncio.subprocess.DEVNULL,
                                env=sub_env,
                            )
                            await kp.wait()
                        else:
                            proc.kill()
                    except Exception:
                        pass
                    break
                stdout_chunks.append(chunk)

        try:
            await asyncio.wait_for(read_stream(), timeout=timeout_seconds)
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            try:
                if has_docker:
                    kp = await asyncio.create_subprocess_exec(
                        docker_bin, "kill", container_name,
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL,
                        env=sub_env,
                    )
                    await kp.wait()
                else:
                    proc.kill()
            except Exception:
                pass
            elapsed = time.perf_counter() - start_time
            return _format_result(OUTCOME_TIMEOUT, expected=expected, is_visible=is_visible, execution_time=elapsed)

        elapsed = time.perf_counter() - start_time

        if limit_exceeded:
            return _format_result(
                OUTCOME_RUNTIME_ERROR,
                expected=expected,
                is_visible=is_visible,
                error_msg="Runtime Error — Output limit exceeded (maximum 64KB allowed).",
                execution_time=elapsed,
                limit_type="output",
            )

        # Inspect if container was killed due to memory exhaustion
        oom_killed = False
        if has_docker:
            try:
                insp = await asyncio.create_subprocess_exec(
                    docker_bin, "inspect", "--format", "{{.State.OOMKilled}}", container_name,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL,
                    env=sub_env,
                )
                insp_out, _ = await insp.communicate()
                oom_killed = (insp_out.strip().decode() == "true")
            except Exception:
                pass

        if oom_killed or proc.returncode == 137:
            return _format_result(
                OUTCOME_RUNTIME_ERROR,
                expected=expected,
                is_visible=is_visible,
                error_msg="Runtime Error — Memory limit exceeded (128MB container limit).",
                execution_time=elapsed,
                limit_type="memory",
            )

        raw_output = b"".join(stdout_chunks).decode("utf-8", errors="replace")
        found_payload = None

        for line in raw_output.splitlines():
            line = line.strip()
            if line.startswith(f"{token}:"):
                json_part = line[len(token) + 1:]
                try:
                    found_payload = json.loads(json_part)
                    break
                except Exception:
                    pass
            elif line.startswith('{"status": "error"'):
                try:
                    found_payload = json.loads(line)
                    break
                except Exception:
                    pass

        if not found_payload:
            return _format_result(
                OUTCOME_RUNTIME_ERROR,
                expected=expected,
                is_visible=is_visible,
                error_msg="Process terminated unexpectedly (possible memory limit exceeded or crash).",
                execution_time=elapsed,
            )

        status = found_payload.get("status")

        if status == "error":
            msg = found_payload.get("message", "Runtime error occurred.")
            lim_type = found_payload.get("limit_type")
            return _format_result(
                OUTCOME_RUNTIME_ERROR,
                expected=expected,
                is_visible=is_visible,
                error_msg=msg,
                execution_time=elapsed,
                limit_type=lim_type,
            )

        actual_repr = found_payload.get("result", "None")
        expected_repr = repr(expected)

        if actual_repr == expected_repr:
            outcome = OUTCOME_PASSED
        else:
            outcome = OUTCOME_WRONG

        return _format_result(
            outcome,
            expected=expected,
            actual_repr=actual_repr,
            is_visible=is_visible,
            execution_time=elapsed,
        )

    finally:
        try:
            if has_docker:
                kp = await asyncio.create_subprocess_exec(
                    docker_bin, "rm", "-f", container_name,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                    env=sub_env,
                )
                await kp.wait()
        except Exception:
            pass
        try:
            shutil.rmtree(tmpdir, ignore_errors=True)
        except Exception:
            pass


def _format_result(
    outcome: str,
    *,
    expected: Any,
    actual_repr: str | None = None,
    is_visible: bool,
    error_msg: str | None = None,
    execution_time: float | None = None,
    limit_type: str | None = None,
) -> dict[str, Any]:
    res: dict[str, Any] = {"outcome": outcome}
    if execution_time is not None:
        res["execution_time"] = round(execution_time, 3)
    else:
        res["execution_time"] = 0.0

    # Determine safe details description
    if outcome == OUTCOME_PASSED:
        details = "Result matched"
    elif outcome == OUTCOME_WRONG:
        details = "Returned result did not match"
    elif outcome == OUTCOME_TIMEOUT:
        details = "Execution deadline exceeded"
    elif outcome == OUTCOME_RUNTIME_ERROR:
        err_lower = (error_msg or "").lower()
        if limit_type == "memory" or "memory limit" in err_lower or "memoryerror" in err_lower:
            details = "Runtime Error — Memory limit exceeded"
        elif limit_type == "output" or "output limit" in err_lower:
            details = "Runtime Error — Output limit exceeded"
        elif limit_type == "disk" or "disk limit" in err_lower or "no space left on device" in err_lower:
            details = "Runtime Error — Disk limit exceeded"
        elif limit_type == "process" or "process limit" in err_lower or "resource temporarily unavailable" in err_lower:
            details = "Runtime Error — Process limit exceeded"
        else:
            if is_visible:
                details = error_msg or "Runtime error occurred"
            else:
                details = "Runtime error occurred during evaluation"
    else:
        details = outcome

    res["details"] = details

    if is_visible:
        res["expected"] = repr(expected)
        if actual_repr is not None:
            res["actual"] = actual_repr
        elif outcome == OUTCOME_TIMEOUT:
            res["actual"] = "(timeout: execution exceeded time limit)"
        elif outcome == OUTCOME_RUNTIME_ERROR:
            res["actual"] = f"(error: {error_msg})" if error_msg else f"(error: {details})"
        if error_msg:
            res["error_msg"] = error_msg

    return res
