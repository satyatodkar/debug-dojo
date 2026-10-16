"""
sandbox/runner.py — Supervisor script that runs INSIDE the Docker container.
"""

import sys
import os
import json
import importlib.util
import traceback

MAX_OUTPUT_BYTES = 8192
MAX_REPR_BYTES   = 4096

class BoundedWriter:
    """Redirects learner print statements and enforces a strict byte cap."""
    def __init__(self, limit: int = MAX_OUTPUT_BYTES):
        self.limit = limit
        self.written = 0

    def write(self, text: str):
        if not text:
            return
        encoded_len = len(text.encode("utf-8", errors="replace"))
        self.written += encoded_len
        if self.written > self.limit:
            # Enforced limit violation: terminate immediately
            payload = {
                "status": "error",
                "message": f"Output limit exceeded (maximum {self.limit} bytes allowed).",
            }
            sys.__stdout__.write(json.dumps(payload) + "\n")
            sys.__stdout__.flush()
            os._exit(1)

    def flush(self):
        pass

def main():
    # ── Read task input ──────────────────────────────────────────────────
    try:
        with open("/task/input.json", "r", encoding="utf-8") as f:
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
    learner_out = BoundedWriter(MAX_OUTPUT_BYTES)
    sys.stdout = learner_out
    sys.stderr = learner_out

    # ── Load learner module ──────────────────────────────────────────────
    try:
        spec_obj = importlib.util.spec_from_file_location("learner_code", "/task/code.py")
        if spec_obj is None or spec_obj.loader is None:
            raise ImportError("Could not load /task/code.py")
        module = importlib.util.module_from_spec(spec_obj)
        spec_obj.loader.exec_module(module)
    except Exception:
        # Module-level error (SyntaxError, NameError at import, etc.)
        tb = traceback.format_exc(limit=3)
        short = "\n".join(tb.strip().splitlines()[-2:])
        payload = {"status": "error", "message": short}
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
    except Exception:
        tb = traceback.format_exc(limit=3)
        short = "\n".join(tb.strip().splitlines()[-2:])
        payload = {"status": "error", "message": short}
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
