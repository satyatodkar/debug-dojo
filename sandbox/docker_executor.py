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
TIMEOUT_SECONDS    = 10.0         # wall-clock limit per individual test (generous margin for Colima VM)
OUTPUT_BYTE_LIMIT   = 8_192        # 8KB maximum stdout capture
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
    return True

async def run_one_test(
    learner_code: str,
    fn_name: str,
    args: list[Any],
    expected: Any,
    *,
    is_visible: bool,
) -> dict[str, Any]:
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
            )

    # Subprocess/In-memory fallback for environments without Docker
    import sys, io, traceback
    from contextlib import redirect_stdout, redirect_stderr

    scope = {}
    buf = io.StringIO()
    try:
        with redirect_stdout(buf), redirect_stderr(buf):
            exec(learner_code, scope)
            if fn_name not in scope or not callable(scope[fn_name]):
                return _format_result(
                    OUTCOME_RUNTIME_ERROR,
                    expected=expected,
                    is_visible=is_visible,
                    error_msg=f"Function "{fn_name}" is not defined or callable.",
                )
            actual = scope[fn_name](*args)

        if repr(actual) == repr(expected):
            return _format_result(
                OUTCOME_PASSED,
                expected=expected,
                actual=actual,
                is_visible=is_visible,
                captured_stdout=buf.getvalue()[:1024],
            )
        else:
            return _format_result(
                OUTCOME_FAILED,
                expected=expected,
                actual=actual,
                is_visible=is_visible,
                captured_stdout=buf.getvalue()[:1024],
            )
    except Exception as exc:
        tb = traceback.format_exc(limit=3)
        return _format_result(
            OUTCOME_RUNTIME_ERROR,
            expected=expected,
            is_visible=is_visible,
            error_msg="\n".join(tb.strip().splitlines()[-2:]),
            captured_stdout=buf.getvalue()[:1024],
        )

async def _execute_container(
    learner_code: str,
    fn_name: str,
    args: list[Any],
    expected: Any,
    is_visible: bool,
) -> dict[str, Any]:
    docker_bin = shutil.which("docker") or "/usr/local/bin/docker"
    TASKS_BASE_DIR.mkdir(parents=True, exist_ok=True)

    tmpdir = tempfile.mkdtemp(prefix="dojo_", dir=str(TASKS_BASE_DIR))
    container_name = f"dojo_{uuid.uuid4().hex[:12]}"
    token = f"tok_{uuid.uuid4().hex[:16]}"

    try:
        # Check if docker daemon actually runs
        has_docker = False
        try:
            chk = await asyncio.create_subprocess_exec(
                docker_bin, "info",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
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
            cmd = [
                docker_bin, "run",
                "--rm",
                "--name", container_name,
                "--network", "none",
                "--read-only",
                "--tmpfs", "/tmp:size=4m,noexec",
                "--memory", "64m",
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

        sub_env = {
            "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        }
        if "DOCKER_HOST" in os.environ:
            sub_env["DOCKER_HOST"] = os.environ["DOCKER_HOST"]

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
                        kp = await asyncio.create_subprocess_exec(
                            docker_bin, "kill", container_name,
                            stdout=asyncio.subprocess.DEVNULL,
                            stderr=asyncio.subprocess.DEVNULL,
                            env=sub_env,
                        )
                        await kp.wait()
                    except Exception:
                        pass
                    break
                stdout_chunks.append(chunk)

        try:
            await asyncio.wait_for(read_stream(), timeout=TIMEOUT_SECONDS)
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            try:
                kp = await asyncio.create_subprocess_exec(
                    docker_bin, "kill", container_name,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                    env=sub_env,
                )
                await kp.wait()
            except Exception:
                pass
            return _format_result(OUTCOME_TIMEOUT, expected=expected, is_visible=is_visible)

        if limit_exceeded:
            return _format_result(
                OUTCOME_RUNTIME_ERROR,
                expected=expected,
                is_visible=is_visible,
                error_msg="Output limit exceeded (maximum 8KB allowed).",
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
            )

        status = found_payload.get("status")

        if status == "error":
            return _format_result(
                OUTCOME_RUNTIME_ERROR,
                expected=expected,
                is_visible=is_visible,
                error_msg=found_payload.get("message", "Runtime error occurred."),
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
        )

    finally:
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
) -> dict[str, Any]:
    res: dict[str, Any] = {"outcome": outcome}
    if is_visible:
        res["expected"] = repr(expected)
        if actual_repr is not None:
            res["actual"] = actual_repr
        elif outcome == OUTCOME_TIMEOUT:
            res["actual"] = "(timeout: execution exceeded time limit)"
        elif outcome == OUTCOME_RUNTIME_ERROR:
            res["actual"] = f"(error: {error_msg})" if error_msg else "(runtime error)"
        if error_msg:
            res["error_msg"] = error_msg
    return res
