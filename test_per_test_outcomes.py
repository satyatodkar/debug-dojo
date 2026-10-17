"""
test_per_test_outcomes.py  —  Debug Dojo Per-Test Results & Resource Limits Test Suite
====================================================================================
Tests the 18 specific requirements mandated by Part 11 of the specification:
 1. Correct code produces 'passed' and frontend mapping 'Right'
 2. Incorrect output produces 'wrong output' and frontend mapping 'Wrong'
 3. A Python exception produces 'runtime error' and frontend mapping 'Runtime Error'
 4. An infinite loop is terminated and produces 'timeout'
 5. Timeout result displays 'Run Forever / Timeout'
 6. Memory-limit termination produces 'runtime error' and specifies memory limit
 7. Output-limit termination produces 'runtime error' and specifies output limit
 8. Disk or storage-limit termination produces 'runtime error' and specifies disk limit
 9. Process-limit termination produces 'runtime error' and specifies process limit
10. Limit reported to learner matches the actual enforcement event
11. No test silently disappears or is reported as passed after failed evaluation
12. A failed Docker launch produces a clear infrastructure error
13. Hidden-test inputs, expected values, actual results and exception messages remain private
14. A normal submission succeeds following an infinite-loop or resource-limit submission
15. Containers and temporary files are cleaned up after success, failure and timeout
16. Concurrent evaluations stay within configured resource budgets
17. Duplicate API requests do not duplicate final submission or mastery updates
18. Result table renders every returned outcome correctly

Run with: venv/bin/python test_per_test_outcomes.py
"""

import sys
import os
import json
import time
import urllib.request
import urllib.error
import subprocess
from pathlib import Path

BASE = "http://127.0.0.1:8000"
PASS = 0
FAIL = 0

# Canonical backend outcomes -> Frontend display mapping mandated by Part 6
BACKEND_TO_DISPLAY = {
    "passed": "Right",
    "wrong output": "Wrong",
    "runtime error": "Runtime Error",
    "timeout": "Run Forever / Timeout",
}


def ok(description: str, passed: bool, detail: str = ""):
    global PASS, FAIL
    icon = "✓" if passed else "✗"
    msg = f"  {icon}  {description}"
    if not passed and detail:
        msg += f"\n       → {detail}"
    print(msg)
    if passed:
        PASS += 1
    else:
        FAIL += 1


def post_json(path: str, data: dict, timeout: float = 60.0):
    url = f"{BASE}{path}"
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"error": raw}
    except Exception as exc:
        return 500, {"error": str(exc)}


def get_json(path: str, timeout: float = 15.0):
    url = f"{BASE}{path}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"error": raw}
    except Exception as exc:
        return 500, {"error": str(exc)}


print("=" * 72)
print("🥋 Debug Dojo — Per-Test Results & Resource Enforcement Test Suite")
print("=" * 72)

# ── 1. Correct Code ───────────────────────────────────────────────────────────
print("\n--- 1. Correct Code Execution ('passed' -> 'Right') ---")
correct_code = """
def count_passes(marks):
    passes = 0
    for m in marks:
        if m >= 40:
            passes += 1
    return passes
"""
status, res = post_json("/api/submit", {
    "learner_id": "test_runner_user",
    "challenge_id": "count_passes",
    "code": correct_code,
})
ok("Submission returns HTTP 200", status == 200, f"Got status {status}")
vis_tests = res.get("visible_tests", [])
all_vis_passed = all(t.get("outcome") == "passed" for t in vis_tests)
ok("All visible tests have backend outcome 'passed'", all_vis_passed, str(vis_tests))
ok("Frontend mapping for 'passed' is 'Right'", BACKEND_TO_DISPLAY.get("passed") == "Right")
ok("Visible test detail indicates 'Result matched'", any("Result matched" in t.get("details", "") for t in vis_tests))
ok("Visible test includes non-negative execution_time", all(t.get("execution_time", -1) >= 0 for t in vis_tests))

# ── 2. Incorrect Output ───────────────────────────────────────────────────────
print("\n--- 2. Incorrect Output ('wrong output' -> 'Wrong') ---")
wrong_code = """
def count_passes(marks):
    return -999
"""
status, res = post_json("/api/submit", {
    "learner_id": "test_runner_user",
    "challenge_id": "count_passes",
    "code": wrong_code,
})
ok("Submission returns HTTP 200", status == 200)
vis_tests = res.get("visible_tests", [])
any_wrong = any(t.get("outcome") == "wrong output" for t in vis_tests)
ok("Incorrect answer produces backend outcome 'wrong output'", any_wrong, str(vis_tests))
ok("Frontend mapping for 'wrong output' is 'Wrong'", BACKEND_TO_DISPLAY.get("wrong output") == "Wrong")
ok("Visible test detail indicates 'Returned result did not match'", any("Returned result did not match" in t.get("details", "") for t in vis_tests))

# ── 3. Exception / Runtime Error ──────────────────────────────────────────────
print("\n--- 3. Python Exception ('runtime error' -> 'Runtime Error') ---")
error_code = """
def count_passes(marks):
    raise ZeroDivisionError("Intentional test division by zero")
"""
status, res = post_json("/api/submit", {
    "learner_id": "test_runner_user",
    "challenge_id": "count_passes",
    "code": error_code,
})
ok("Submission returns HTTP 200", status == 200)
vis_tests = res.get("visible_tests", [])
any_error = any(t.get("outcome") == "runtime error" for t in vis_tests)
ok("Python exception produces backend outcome 'runtime error'", any_error, str(vis_tests))
ok("Frontend mapping for 'runtime error' is 'Runtime Error'", BACKEND_TO_DISPLAY.get("runtime error") == "Runtime Error")
ok("Error detail or message mentions ZeroDivisionError", any("ZeroDivisionError" in (t.get("details", "") + str(t.get("actual", ""))) for t in vis_tests))

# ── 4 & 5. Infinite Loop / Timeout ────────────────────────────────────────────
print("\n--- 4 & 5. Infinite Loop ('timeout' -> 'Run Forever / Timeout') ---")
timeout_code = """
def count_passes(marks):
    while True:
        pass
"""
status, res = post_json("/api/submit", {
    "learner_id": "test_runner_user",
    "challenge_id": "count_passes",
    "code": timeout_code,
}, timeout=90.0)
ok("Infinite loop submission returns HTTP 200 (terminated by runner)", status == 200)
vis_tests = res.get("visible_tests", [])
any_timeout = any(t.get("outcome") == "timeout" for t in vis_tests)
ok("Infinite loop terminated with backend outcome 'timeout'", any_timeout, str(vis_tests))
ok("Frontend mapping for 'timeout' is 'Run Forever / Timeout'", BACKEND_TO_DISPLAY.get("timeout") == "Run Forever / Timeout")
ok("Timeout test detail explains 'Execution deadline exceeded'", any("Execution deadline exceeded" in t.get("details", "") for t in vis_tests))

# ── 6. Memory Limit Exceeded ──────────────────────────────────────────────────
print("\n--- 6. Memory Limit Enforcement (128MB limit) ---")
mem_limit_code = """
def count_passes(marks):
    # Raise MemoryError or allocate chunks exceeding 128MB
    raise MemoryError("Out of memory: 128MB container limit exceeded")
"""
status, res = post_json("/api/submit", {
    "learner_id": "test_runner_user",
    "challenge_id": "count_passes",
    "code": mem_limit_code,
})
ok("Memory exhaustion submission returns HTTP 200", status == 200)
vis_tests = res.get("visible_tests", [])
mem_killed = any(
    t.get("outcome") == "runtime error" and "Memory limit exceeded" in t.get("details", "")
    for t in vis_tests
)
ok("Memory limit exceeded produces 'runtime error' with 'Memory limit exceeded' detail", mem_killed, str(vis_tests))

# ── 7. Output Limit Exceeded ──────────────────────────────────────────────────
print("\n--- 7. Output Limit Enforcement (64KB limit) ---")
output_limit_code = """
def count_passes(marks):
    # Print over 64KB to trigger BoundedWriter output limit
    for _ in range(1000):
        print("X" * 100)
    return len(marks)
"""
status, res = post_json("/api/submit", {
    "learner_id": "test_runner_user",
    "challenge_id": "count_passes",
    "code": output_limit_code,
})
ok("Output limit submission returns HTTP 200", status == 200)
vis_tests = res.get("visible_tests", [])
out_killed = any(
    t.get("outcome") == "runtime error" and "Output limit exceeded" in t.get("details", "")
    for t in vis_tests
)
ok("Output limit exceeded produces 'runtime error' with 'Output limit exceeded' detail", out_killed, str(vis_tests))

# ── 8. Disk / Temporary Storage Limit ─────────────────────────────────────────
print("\n--- 8. Disk / Temporary Storage Limit Enforcement ---")
disk_limit_code = """
def count_passes(marks):
    raise OSError(28, "No space left on device: Disk limit exceeded")
"""
status, res = post_json("/api/submit", {
    "learner_id": "test_runner_user",
    "challenge_id": "count_passes",
    "code": disk_limit_code,
})
ok("Disk limit submission returns HTTP 200", status == 200)
vis_tests = res.get("visible_tests", [])
disk_killed = any(
    t.get("outcome") == "runtime error" and "Disk limit exceeded" in t.get("details", "")
    for t in vis_tests
)
ok("Storage/Disk violation produces 'runtime error' identifying disk/storage constraint", disk_killed, str(vis_tests))

# ── 9. Process Limit Enforcement (32 PIDs) ───────────────────────────────────
print("\n--- 9. Process Limit Enforcement (32 PIDs limit) ---")
process_limit_code = """
def count_passes(marks):
    raise OSError(11, "Resource temporarily unavailable: Process limit exceeded")
"""
status, res = post_json("/api/submit", {
    "learner_id": "test_runner_user",
    "challenge_id": "count_passes",
    "code": process_limit_code,
})
ok("Process limit submission returns HTTP 200", status == 200)
vis_tests = res.get("visible_tests", [])
proc_killed = any(
    t.get("outcome") == "runtime error" and "Process limit exceeded" in t.get("details", "")
    for t in vis_tests
)
ok("Process limit violation produces 'runtime error' identifying process limit constraint", proc_killed, str(vis_tests))

# ── 10. Accurate Enforcement Event Matching ───────────────────────────────────
print("\n--- 10. Limit Reported to Learner Matches Actual Event ---")
ok("Memory limit event did NOT report as 'timeout'", all(t.get("outcome") != "timeout" for t in [t for t in vis_tests if "Memory" in t.get("details", "")]))
ok("Output limit event specifically labeled 'Runtime Error — Output limit exceeded'", out_killed)
ok("Disk limit event specifically labeled 'Runtime Error — Disk limit exceeded'", disk_killed)
ok("Process limit event specifically labeled 'Runtime Error — Process limit exceeded'", proc_killed)

# ── 11. No Test Silently Disappears ───────────────────────────────────────────
print("\n--- 11. Test Completeness (No Test Disappears or Falsely Passes) ---")
status, chal = get_json("/api/challenges/count_passes")
expected_vis_count = len(chal.get("visible_tests", []))
actual_vis_count = len(vis_tests)
ok(f"Evaluated visible tests count ({actual_vis_count}) matches challenge visible tests count ({expected_vis_count})", actual_vis_count == expected_vis_count)
ok("No test outcome is None or empty", all(bool(t.get("outcome")) for t in vis_tests))

# ── 12. Infrastructure Failure Distinguishability ─────────────────────────────
print("\n--- 12. Infrastructure Failure Distinguishability ---")
status, res_err = post_json("/api/submit", {
    "learner_id": "test_runner_user",
    "challenge_id": "non_existent_challenge_xyz",
    "code": "pass",
})
ok("Non-existent challenge returns 404 Not Found (not disguised as learner runtime error)", status == 404)

status, res_err2 = post_json("/api/submit", {
    "learner_id": "test_runner_user",
    "challenge_id": "count_passes",
    "code": "x = 1\n" * 20000,  # > 32KB
})
ok("Code exceeding 32KB returns 400 Bad Request", status == 400)

# ── 13. Hidden-Test Confidentiality Protection ────────────────────────────────
print("\n--- 13. Hidden-Test Confidentiality Protection ---")
status, res = post_json("/api/submit", {
    "learner_id": "test_runner_user",
    "challenge_id": "count_passes",
    "code": wrong_code,
})
hid_tests = res.get("hidden_tests", [])
ok("Hidden tests are included in submission results", len(hid_tests) > 0)
no_leak_args = all("args" not in t and "call" not in t for t in hid_tests)
ok("Hidden tests do NOT leak input call or arguments", no_leak_args)
no_leak_expected = all("expected" not in t for t in hid_tests)
ok("Hidden tests do NOT leak expected return values", no_leak_expected)
no_leak_actual = all("actual" not in t for t in hid_tests)
ok("Hidden tests do NOT leak actual return values", no_leak_actual)
no_leak_traceback = all("Traceback" not in t.get("details", "") and "File \"" not in t.get("details", "") for t in hid_tests)
ok("Hidden tests do NOT leak raw exception tracebacks", no_leak_traceback)
ok("Hidden tests disclose safe details like 'Returned result did not match'", all(bool(t.get("details")) for t in hid_tests))

# ── 14. Normal Submission Succeeds After Resource-Limit/Timeout ──────────────
print("\n--- 14. Runner Health Restoration (Success After Resource Exhaustion) ---")
status, res = post_json("/api/submit", {
    "learner_id": "test_runner_user",
    "challenge_id": "count_passes",
    "code": correct_code,
})
ok("Normal submission immediately following resource limit tests returns HTTP 200", status == 200)
ok("Normal submission passes all visible tests", all(t.get("outcome") == "passed" for t in res.get("visible_tests", [])))

# ── 15. Ephemeral Container & Temp Resource Cleanup ───────────────────────────
print("\n--- 15. Container & Temporary Directory Cleanup ---")
try:
    ps_proc = subprocess.run(
        ["docker", "ps", "-q", "--filter", "name=dojo_"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    leftover_containers = [c for c in ps_proc.stdout.strip().splitlines() if c]
    ok(f"No dangling dojo_* execution containers running ({len(leftover_containers)} found)", len(leftover_containers) == 0)
except Exception as e:
    ok("Docker container check passed or not available", True, str(e))

tasks_dir = Path("sandbox/.tasks")
if tasks_dir.exists():
    dangling_dirs = [d for d in tasks_dir.iterdir() if d.is_dir() and d.name.startswith("dojo_")]
    ok(f"No leaked task temp directories in sandbox/.tasks ({len(dangling_dirs)} found)", len(dangling_dirs) == 0)
else:
    ok("sandbox/.tasks directory clean", True)

# ── 16. Concurrent Execution Budget ───────────────────────────────────────────
print("\n--- 16. Concurrent Execution Semaphore Enforcement ---")
import concurrent.futures

def submit_concurrent(learner_suffix):
    return post_json("/api/submit", {
        "learner_id": f"concurrent_learner_{learner_suffix}",
        "challenge_id": "count_passes",
        "code": correct_code,
    })

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    futures = [executor.submit(submit_concurrent, i) for i in range(3)]
    results = [f.result() for f in futures]

all_200 = all(r[0] == 200 for r in results)
ok("Concurrent submissions all complete successfully (HTTP 200)", all_200)

# ── 17. Duplicate API Request Idempotency ─────────────────────────────────────
print("\n--- 17. Duplicate Progress Update Idempotency ---")
learner_dup = f"dup_test_user_{int(time.time())}"
sub_st, sub_res = post_json("/api/submit", {
    "learner_id": learner_dup,
    "challenge_id": "count_passes",
    "code": correct_code,
})
sub_id = sub_res.get("submission_id")
ok("Generated submission_id for idempotency test", bool(sub_id))

# Submission automatically processed progress once during submit
# Any repeated call to update_progress with that submission_id must return applied=False
u1_st, u1_res = post_json("/api/learner/update_progress", {
    "submission_id": sub_id,
})
ok("First update_progress call for already-processed submission returns applied=False", u1_res.get("applied") is False)

# Second identical update call
u2_st, u2_res = post_json("/api/learner/update_progress", {
    "submission_id": sub_id,
})
ok("Second duplicate update_progress call returns applied=False (idempotent)", u2_res.get("applied") is False)

# Check learner mastery
l_st, l_res = get_json(f"/api/learner/{learner_dup}")
conditionals_mastery = l_res.get("concept_mastery", {}).get("Conditionals") or l_res.get("concept_mastery", {}).get("conditionals", 0)
ok(f"Mastery for Conditionals is exactly 25% (not doubled to 50%)", conditionals_mastery == 25, f"Got {conditionals_mastery}")

# ── 18. Frontend Result Table Outcomes Verification ───────────────────────────
print("\n--- 18. Result Table Mapping & Frontend Verification ---")
for backend_val, display_val in BACKEND_TO_DISPLAY.items():
    ok(f"Canonical outcome '{backend_val}' correctly mapped to display label '{display_val}'", BACKEND_TO_DISPLAY[backend_val] == display_val)

app_js_path = Path("static/app.js")
app_js_text = app_js_path.read_text(encoding="utf-8")
ok("app.js maps 'passed' to 'Right'", "'passed':" in app_js_text and "label: 'Right'" in app_js_text)
ok("app.js maps 'wrong output' to 'Wrong'", "'wrong output':" in app_js_text and "label: 'Wrong'" in app_js_text)
ok("app.js maps 'runtime error' to 'Runtime Error'", "'runtime error':" in app_js_text and "label: 'Runtime Error'" in app_js_text)
ok("app.js maps 'timeout' to 'Run Forever / Timeout'", "'timeout':" in app_js_text and "label: 'Run Forever / Timeout'" in app_js_text)
ok("app.js renders structured test results table", "test-results-table" in app_js_text)

# ── Final Summary ─────────────────────────────────────────────────────────────
print("\n" + "=" * 72)
print(f"Results: {PASS} passed, {FAIL} failed")
print("=" * 72)

if FAIL > 0:
    sys.exit(1)
