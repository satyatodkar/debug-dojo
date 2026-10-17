"""
sandbox/runner.py — Supervisor script that runs INSIDE the Docker container.
"""

import sys
import os
import json
import importlib.util
import traceback

MAX_OUTPUT_BYTES = 65536  # 64 KiB output limit
MAX_REPR_BYTES   = 16384

class BoundedWriter:
    """Redirects learner print statements and enforces a strict byte cap."""
    def __init__(self, limit: int = MAX_OUTPUT_BYTES, token: str = ""):
        self.limit = limit
        self.token = token
        self.written = 0

    def write(self, text: str):
        if not text:
            return
        encoded_len = len(text.encode("utf-8", errors="replace"))
        self.written += encoded_len
        if self.written > self.limit:
            # Enforced limit violation: terminate immediately with structured payload
            payload = {
                "status": "error",
                "message": "Runtime Error — Output limit exceeded (maximum 64KB allowed).",
                "limit_type": "output",
            }
            prefix = f"{self.token}:" if self.token else ""
            sys.__stdout__.write(f"{prefix}{json.dumps(payload)}\n")
            sys.__stdout__.flush()
            os._exit(0)

    def flush(self):
        pass


def _classify_runtime_exception(exc: Exception) -> dict:
    """Classify exceptions into specific resource limit errors or standard runtime errors."""
    err_str = str(exc).lower()
    exc_type = type(exc).__name__

    if isinstance(exc, MemoryError) or "memoryerror" in err_str or "out of memory" in err_str:
        return {
            "status": "error",
            "message": "Runtime Error — Memory limit exceeded (128MB memory limit).",
            "limit_type": "memory",
        }

    errno = getattr(exc, "errno", None)
    if errno == 28 or "no space left on device" in err_str:
        return {
            "status": "error",
            "message": "Runtime Error — Disk limit exceeded (temporary storage limit exceeded).",
            "limit_type": "disk",
        }

    if errno == 11 or "resource temporarily unavailable" in err_str or "can't start new thread" in err_str:
        return {
            "status": "error",
            "message": "Runtime Error — Process limit exceeded (maximum 32 processes allowed).",
            "limit_type": "process",
        }

    tb = traceback.format_exc(limit=3)
    short = "\n".join(tb.strip().splitlines()[-2:])
    return {"status": "error", "message": short}


def main():
    # ── Read task input ──────────────────────────────────────────────────
    task_dir = sys.argv[1] if len(sys.argv) > 1 else "/task"
    try:
        with open(os.path.join(task_dir, "input.json"), "r", encoding="utf-8") as f:
            spec = json.load(f)
        fn_name = spec["fn"]
        args    = spec.get("args", [])
        token   = spec.get("token", "")
    except Exception as exc:
        payload = {"status": "error", "message": f"Runner input read error: {exc}"}
        sys.__stdout__.write(json.dumps(payload) + "\n")
        sys.__stdout__.flush()
        sys.exit(1)

    # ── Install bounded stdout/stderr for learner code ───────────────────
    learner_out = BoundedWriter(MAX_OUTPUT_BYTES, token=token)
    sys.stdout = learner_out
    sys.stderr = learner_out

    # ── Load learner module ──────────────────────────────────────────────
    try:
        spec_obj = importlib.util.spec_from_file_location("learner_code", os.path.join(task_dir, "code.py"))
        if spec_obj is None or spec_obj.loader is None:
            raise ImportError("Could not load /task/code.py")
        module = importlib.util.module_from_spec(spec_obj)
        spec_obj.loader.exec_module(module)
    except Exception as exc:
        payload = _classify_runtime_exception(exc)
        sys.__stdout__.write(f"{token}:{json.dumps(payload)}\n")
        sys.__stdout__.flush()
        sys.exit(0)

    # ── Retrieve target function ─────────────────────────────────────────
    fn = getattr(module, fn_name, None)
    if fn is None or not callable(fn):
        payload = {"status": "error", "message": f"Function '{fn_name}' not defined in submitted code."}
        sys.__stdout__.write(f"{token}:{json.dumps(payload)}\n")
        sys.__stdout__.flush()
        sys.exit(0)

    # ── Execute target function ──────────────────────────────────────────
    try:
        result = fn(*args)
    except Exception as exc:
        payload = _classify_runtime_exception(exc)
        sys.__stdout__.write(f"{token}:{json.dumps(payload)}\n")
        sys.__stdout__.flush()
        sys.exit(0)

    # ── Format result ────────────────────────────────────────────────────
    if result is None:
        payload = {"status": "no_return", "result": "None"}
    else:
        result_repr = repr(result)
        if len(result_repr.encode("utf-8", errors="replace")) > MAX_REPR_BYTES:
            result_repr = result_repr[:MAX_REPR_BYTES] + "…(truncated)"
        payload = {"status": "ok", "result": result_repr}

    sys.__stdout__.write(f"{token}:{json.dumps(payload)}\n")
    sys.__stdout__.flush()

if __name__ == "__main__":
    main()
