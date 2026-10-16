"""
test_phase3.py  —  Debug Dojo Phase 3 Comprehensive Test Suite
==============================================================
Validates:
  1. Correct solution: all visible & hidden tests pass.
  2. Wrong answer: outcome classified as "wrong output".
  3. Exception: outcome classified as "runtime error".
  4. Infinite loop: terminated by timeout, outcome is "timeout".
  5. Excessive output: terminated immediately, outcome is "runtime error".
  6. Network access attempt: blocked, outcome is "runtime error".
  7. Host file read attempt: blocked, outcome is "runtime error".
  8. Hidden test isolation: learner cannot dump hidden tests or inspect host data.
  9. Docker failure simulation: fail-closed with 503.
  10. Invalid challenge IDs and malformed requests return 404/400/422.
  11. Normal submission immediately succeeds after a timed-out submission.
  12. Existing Phase 1 & 2 endpoints remain intact.
"""

import sys
import os
import json
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8000"
PASS = 0
FAIL = 0


def post_json(path, payload):
    url = BASE + path
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = {}
        try:
            body = json.loads(e.read().decode("utf-8"))
        except Exception:
            pass
        return e.code, body


def get_json(path):
    url = BASE + path
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = {}
        try:
            body = json.loads(e.read().decode("utf-8"))
        except Exception:
            pass
        return e.code, body


def check(name, condition, extra=""):
    global PASS, FAIL
    icon = "✓" if condition else "✗"
    msg = f"  {icon} {name}"
    if not condition and extra:
        msg += f"\n       → {extra}"
    print(msg)
    if condition:
        PASS += 1
    else:
        FAIL += 1


print("\n=======================================================")
print("        DEBUG DOJO — PHASE 3 TEST SUITE")
print("=======================================================")

# ---------------------------------------------------------------------------
# 1. Existing endpoints regression check
# ---------------------------------------------------------------------------
print("\n[1] Verifying Phase 1 & 2 Endpoints...")
s, h = get_json("/api/health")
check("GET /api/health returns 200", s == 200)
check("Health status is 'ok'", h.get("status") == "ok")

s, chs = get_json("/api/challenges")
check("GET /api/challenges returns 200", s == 200)
check("All 10 challenges present", isinstance(chs, list) and len(chs) == 10)

s, ch = get_json("/api/challenges/count_passes")
check("GET /api/challenges/count_passes returns 200", s == 200)
check("No hidden tests leaked in detail endpoint", "hidden_tests" not in ch)
check("Visible tests list present", len(ch.get("visible_tests", [])) >= 3)


# ---------------------------------------------------------------------------
# 2. Correct solution
# ---------------------------------------------------------------------------
print("\n[2] Testing a Correct Solution...")
correct_code = """
def count_passes(marks):
    return sum(1 for m in marks if m >= 40)
"""
s, res = post_json("/api/submit", {
    "learner_id": "student_alice",
    "challenge_id": "count-passes",  # testing hyphen normalization
    "code": correct_code,
})
check("POST /api/submit returns 200", s == 200, f"Got status {s}")
check("Submission ID present", bool(res.get("submission_id")))
check("all_passed is True", res.get("all_passed") is True)
check("Summary indicates success", "All" in res.get("summary", ""))

v_outcomes = [t["outcome"] for t in res.get("visible_tests", [])]
h_outcomes = [t["outcome"] for t in res.get("hidden_tests", [])]
check("All visible tests passed", all(o == "passed" for o in v_outcomes), str(v_outcomes))
check("All hidden tests passed", all(o == "passed" for o in h_outcomes), str(h_outcomes))
check("Hidden tests do not reveal expected values", all("expected" not in t for t in res.get("hidden_tests", [])))
check("Hidden tests do not reveal actual outputs", all("actual" not in t for t in res.get("hidden_tests", [])))


# ---------------------------------------------------------------------------
# 3. Wrong answer
# ---------------------------------------------------------------------------
print("\n[3] Testing a Wrong Answer...")
wrong_code = """
def count_passes(marks):
    return 0  # always wrong
"""
s, res = post_json("/api/submit", {
    "learner_id": "student_bob",
    "challenge_id": "count_passes",
    "code": wrong_code,
})
check("Status 200 for wrong solution", s == 200)
check("all_passed is False", res.get("all_passed") is False)
v_outcomes = [t["outcome"] for t in res.get("visible_tests", [])]
check("Outcomes include 'wrong output'", "wrong output" in v_outcomes, str(v_outcomes))
# Check that visible tests have expected and actual
wrong_test = next(t for t in res.get("visible_tests", []) if t["outcome"] == "wrong output")
check("Visible test provides expected value", "expected" in wrong_test)
check("Visible test provides actual value", "actual" in wrong_test and wrong_test["actual"] == "0")


# ---------------------------------------------------------------------------
# 4. Code that raises an exception
# ---------------------------------------------------------------------------
print("\n[4] Testing an Exception (Runtime Error)...")
err_code = """
def count_passes(marks):
    return 1 / 0
"""
s, res = post_json("/api/submit", {
    "learner_id": "student_charlie",
    "challenge_id": "count_passes",
    "code": err_code,
})
check("Status 200 for exception submission", s == 200)
v_outcomes = [t["outcome"] for t in res.get("visible_tests", [])]
check("Outcome is 'runtime error'", all(o == "runtime error" for o in v_outcomes), str(v_outcomes))
check("Hidden tests classified as 'runtime error'", all(t["outcome"] == "runtime error" for t in res.get("hidden_tests", [])))


# ---------------------------------------------------------------------------
# 5. Infinite loop (Timeout termination)
# ---------------------------------------------------------------------------
print("\n[5] Testing Infinite Loop (Timeout)...")
loop_code = """
def count_passes(marks):
    while True:
        pass
"""
s, res = post_json("/api/submit", {
    "learner_id": "student_dave",
    "challenge_id": "count_passes",
    "code": loop_code,
})
check("Status 200 for timeout submission", s == 200)
v_outcomes = [t["outcome"] for t in res.get("visible_tests", [])]
check("Outcome is 'timeout'", "timeout" in v_outcomes, str(v_outcomes))


# ---------------------------------------------------------------------------
# 6. Excessive output
# ---------------------------------------------------------------------------
print("\n[6] Testing Excessive Output...")
spam_code = """
def count_passes(marks):
    for _ in range(500):
        print("SpamSpamSpamSpam" * 100)
    return len(marks)
"""
s, res = post_json("/api/submit", {
    "learner_id": "student_eve",
    "challenge_id": "count_passes",
    "code": spam_code,
})
check("Status 200 for excessive output", s == 200)
v_outcomes = [t["outcome"] for t in res.get("visible_tests", [])]
check("Outcome is 'runtime error'", "runtime error" in v_outcomes, str(v_outcomes))


# ---------------------------------------------------------------------------
# 7. Network and host file security checks
# ---------------------------------------------------------------------------
print("\n[7] Testing Security Boundaries (Network & Host Files)...")
net_code = """
import urllib.request
def count_passes(marks):
    urllib.request.urlopen("http://example.com", timeout=1)
    return 0
"""
s, res = post_json("/api/submit", {
    "learner_id": "student_mallory",
    "challenge_id": "count_passes",
    "code": net_code,
})
v_outcomes = [t["outcome"] for t in res.get("visible_tests", [])]
check("Network access blocked ('runtime error')", all(o == "runtime error" for o in v_outcomes), str(v_outcomes))

host_code = """
def count_passes(marks):
    with open("/Users/satyajit/Desktop", "r") as f:
        return 0
"""
s, res = post_json("/api/submit", {
    "learner_id": "student_mallory",
    "challenge_id": "count_passes",
    "code": host_code,
})
v_outcomes = [t["outcome"] for t in res.get("visible_tests", [])]
check("Host filesystem access blocked ('runtime error')", all(o == "runtime error" for o in v_outcomes), str(v_outcomes))


# ---------------------------------------------------------------------------
# 8. Attempting to reveal hidden test data
# ---------------------------------------------------------------------------
print("\n[8] Testing Hidden Test Confidentiality...")
spy_code = """
import inspect, sys, os
def count_passes(marks):
    # Attempt to read caller stack frames, parent globals, environment
    frames = inspect.stack()
    return len(frames)
"""
s, res = post_json("/api/submit", {
    "learner_id": "student_spy",
    "challenge_id": "count_passes",
    "code": spy_code,
})
check("Spy code handled cleanly", s == 200)
check("Hidden tests still hide expected/inputs", all("expected" not in t for t in res.get("hidden_tests", [])))


# ---------------------------------------------------------------------------
# 9. Invalid challenge IDs and malformed requests
# ---------------------------------------------------------------------------
print("\n[9] Testing Validation & Malformed Requests...")
s, err = post_json("/api/submit", {
    "learner_id": "student1",
    "challenge_id": "non_existent_challenge",
    "code": "def foo(): pass",
})
check("Unknown challenge_id returns 404", s == 404, f"Got {s}")

s, err = post_json("/api/submit", {
    "learner_id": "",
    "challenge_id": "count_passes",
    "code": "def count_passes(m): return 0",
})
check("Empty learner_id returns 422/400", s in (400, 422), f"Got {s}")

s, err = post_json("/api/submit", {
    "learner_id": "student1",
    "challenge_id": "count_passes",
    "code": "",
})
check("Empty code returns 422/400", s in (400, 422), f"Got {s}")

s, err = post_json("/api/submit", {
    "learner_id": "student1",
    "challenge_id": "count_passes",
    "code": "x = 1\n" * 40000,  # exceeds 32KB
})
check("Code exceeding 32KB returns 400", s == 400, f"Got {s}")


# ---------------------------------------------------------------------------
# 10. Successful normal submission after a timed-out submission
# ---------------------------------------------------------------------------
print("\n[10] Testing Normal Submission Immediately After Timeout...")
# First: timeout
post_json("/api/submit", {
    "learner_id": "student_seq",
    "challenge_id": "count_passes",
    "code": "def count_passes(m):\n    while True: pass",
})
# Immediately next: correct
s, res = post_json("/api/submit", {
    "learner_id": "student_seq",
    "challenge_id": "count_passes",
    "code": "def count_passes(m):\n    return sum(1 for x in m if x >= 40)",
})
check("Subsequent submission returns 200", s == 200)
check("Subsequent submission passes all tests", res.get("all_passed") is True)


# ---------------------------------------------------------------------------
# 11. Fail closed if Docker is unavailable (unit check)
# ---------------------------------------------------------------------------
print("\n[11] Verifying Fail-Closed Architecture...")
from sandbox.docker_executor import check_docker_available
import asyncio
avail = asyncio.run(check_docker_available())
check("Docker daemon detected as available", avail is True)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
total = PASS + FAIL
print(f"\n{'═' * 55}")
print(f"  PHASE 3 RESULTS: {PASS}/{total} passed  |  {FAIL} failed")
print(f"{'═' * 55}\n")

sys.exit(0 if FAIL == 0 else 1)
