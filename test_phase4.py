"""
test_phase4.py  —  Debug Dojo Phase 4 Comprehensive Test Suite
==============================================================
Validates:
  1. Boundary-comparison bug detection on count_passes.
  2. Plain-language failure explanations for runtime error, timeout, and wrong output.
  3. Progressive hints: Hint 1 (question), Hint 2 (concept), Hint 3 (targeted).
  4. Exhaustion of hints ladder.
  5. No complete solution disclosed in hints or explanations.
  6. Confidentiality of hidden test inputs, expected values, and raw traces.
  7. Proper handling of unknown submission IDs (404) and successful submissions.
  8. False-positive resistance: categories are NOT assigned without supporting evidence.
  9. Regressions check for Phase 1, Phase 2, and Phase 3 endpoints.
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
print("        DEBUG DOJO — PHASE 4 TEST SUITE")
print("=======================================================")

# ---------------------------------------------------------------------------
# 1. Regressions check: Health, Challenges, and Submit
# ---------------------------------------------------------------------------
print("\n[1] Regression Check (Phases 1, 2 & 3)...")
s, h = get_json("/api/health")
check("GET /api/health is ok", s == 200 and h.get("status") == "ok")

s, chs = get_json("/api/challenges")
check("GET /api/challenges returns 10 challenges", s == 200 and len(chs) == 10)

s, ch = get_json("/api/challenges/count_passes")
check("GET /api/challenges/count_passes returns 200", s == 200)
check("Hidden tests not leaked in challenges endpoint", "hidden_tests" not in ch)


# ---------------------------------------------------------------------------
# 2. Boundary-comparison bug detection on count_passes
# ---------------------------------------------------------------------------
print("\n[2] Testing Boundary-Comparison Bug on count_passes...")
buggy_code = """
def count_passes(marks):
    passes = 0
    for mark in marks:
        if mark > 40:  # Bug: > instead of >=
            passes += 1
    return passes
"""
s, res = post_json("/api/submit", {
    "learner_id": "student_debug1",
    "challenge_id": "count_passes",
    "code": buggy_code,
})
check("Status 200 for submission with boundary bug", s == 200)
sub_id = res.get("submission_id")
check("Submission ID returned", bool(sub_id))
check("all_passed is False", res.get("all_passed") is False)

# Check explanation
exp = res.get("explanation", "")
check("Explanation field present in response", bool(exp))
check("Explanation mentions confirmed observation", "Confirmed observation" in exp)
check("Explanation mentions possible cause", "Possible cause" in exp)
check("Explanation mentions boundary", "boundary" in exp.lower() or "comparison" in exp.lower())

# Check mistake taxonomy
mistakes = res.get("mistakes", [])
check("Mistakes list present", isinstance(mistakes, list) and len(mistakes) > 0)
boundary_mistake = next((m for m in mistakes if m.get("category") == "boundary_comparison"), None)
check("category 'boundary_comparison' detected", boundary_mistake is not None)
if boundary_mistake:
    check("Evidence is provided", bool(boundary_mistake.get("evidence")))
    check("Confidence is high", boundary_mistake.get("confidence") == "high")


# ---------------------------------------------------------------------------
# 3. Progressive Hints (Hint 1, 2, 3, and Exhausted)
# ---------------------------------------------------------------------------
print("\n[3] Testing Progressive Hints for the Boundary Bug...")

# Hint 1
s1, h1 = post_json("/api/hint", {"submission_id": sub_id})
check("POST /api/hint #1 returns 200", s1 == 200)
check("Hint 1 has hint_number 1", h1.get("hint_number") == 1)
check("Hint 1 poses a question (contains '?')", "?" in h1.get("hint", ""))
check("Hint 1 has_more is True", h1.get("has_more") is True)

# Hint 2
s2, h2 = post_json("/api/hint", {"submission_id": sub_id})
check("POST /api/hint #2 returns 200", s2 == 200)
check("Hint 2 has hint_number 2", h2.get("hint_number") == 2)
check("Hint 2 directs attention to concept/operator", "operator" in h2.get("hint", "").lower() or ">" in h2.get("hint", ""))
check("Hint 2 has_more is True", h2.get("has_more") is True)

# Hint 3
s3, h3 = post_json("/api/hint", {"submission_id": sub_id})
check("POST /api/hint #3 returns 200", s3 == 200)
check("Hint 3 has hint_number 3", h3.get("hint_number") == 3)
check("Hint 3 narrows down to condition", "loop" in h3.get("hint", "").lower() or "condition" in h3.get("hint", "").lower() or ">=" in h3.get("hint", ""))
check("Hint 3 has_more is False", h3.get("has_more") is False)

# Hint 4: Exhausted
s4, h4 = post_json("/api/hint", {"submission_id": sub_id})
check("POST /api/hint #4 returns 200", s4 == 200)
check("Status is 'exhausted'", h4.get("status") == "exhausted")
check("Hint text is None", h4.get("hint") is None)
check("Exhaustion message provided", "All" in h4.get("message", ""))
check("has_more is False", h4.get("has_more") is False)

# No complete solution verification
full_sol = "def count_passes"
for idx, h_obj in enumerate([h1, h2, h3]):
    txt = h_obj.get("hint", "")
    check(f"Hint #{idx+1} does not give full code solution", full_sol not in txt)


# ---------------------------------------------------------------------------
# 4. Explanations for Runtime Error, Timeout, and Wrong Output
# ---------------------------------------------------------------------------
print("\n[4] Testing Explanations for Different Failure Types...")

# Runtime Error
s, res = post_json("/api/submit", {
    "learner_id": "student_err",
    "challenge_id": "count_passes",
    "code": "def count_passes(m): return 1 / 0",
})
exp_err = res.get("explanation", "")
check("Runtime error explanation identifies runtime error", "runtime error" in exp_err.lower())

# Timeout
s, res = post_json("/api/submit", {
    "learner_id": "student_time",
    "challenge_id": "count_passes",
    "code": "def count_passes(m):\n    while True: pass",
})
exp_time = res.get("explanation", "")
check("Timeout explanation identifies timeout / infinite loop", "timeout" in exp_time.lower() or "loop" in exp_time.lower())

# Wrong Output
s, res = post_json("/api/submit", {
    "learner_id": "student_wrong",
    "challenge_id": "count_passes",
    "code": "def count_passes(m): return -999",
})
exp_wrong = res.get("explanation", "")
check("Wrong output explanation identifies incorrect return value", "incorrect" in exp_wrong.lower() or "return" in exp_wrong.lower())


# ---------------------------------------------------------------------------
# 5. Handling Unknown IDs and Submissions Without Failures
# ---------------------------------------------------------------------------
print("\n[5] Testing Edge Cases for /api/hint...")

# Unknown submission ID
s, err = post_json("/api/hint", {"submission_id": "sub_nonexistent_12345"})
check("Unknown submission_id returns 404", s == 404, f"Got {s}")

# Successful submission
s, res_good = post_json("/api/submit", {
    "learner_id": "student_good",
    "challenge_id": "count_passes",
    "code": "def count_passes(m):\n    return sum(1 for x in m if x >= 40)",
})
good_sub_id = res_good.get("submission_id")
check("Correct submission succeeded", res_good.get("all_passed") is True)

s_hint, h_good = post_json("/api/hint", {"submission_id": good_sub_id})
check("Hint on passed submission returns 200", s_hint == 200)
check("Status indicates completed/no hints needed", h_good.get("status") == "completed")
check("hint field is None", h_good.get("hint") is None)


# ---------------------------------------------------------------------------
# 6. Mistake Taxonomy: False-Positive Resistance
# ---------------------------------------------------------------------------
print("\n[6] Testing Mistake Taxonomy False-Positive Resistance...")
# A simple function returning a fixed wrong number (not an off-by-one, not a boundary issue)
generic_wrong = """
def count_passes(marks):
    return -999
"""
s, res_gen = post_json("/api/submit", {
    "learner_id": "student_gen",
    "challenge_id": "count_passes",
    "code": generic_wrong,
})
gen_mistakes = res_gen.get("mistakes", [])
# It should NOT be tagged as boundary_comparison, mutates_input, or unhandled_short_input
cats = [m.get("category") for m in gen_mistakes]
check("boundary_comparison NOT falsely assigned", "boundary_comparison" not in cats)
check("mutates_input NOT falsely assigned", "mutates_input" not in cats)
check("unhandled_short_input NOT falsely assigned", "unhandled_short_input" not in cats)


# ---------------------------------------------------------------------------
# 7. Privacy & Confidentiality Checks
# ---------------------------------------------------------------------------
print("\n[7] Testing Confidentiality in Explanations & Hints...")
# Verify hidden test inputs or expected answers never leak into explanation or hints
all_hints_text = (h1.get("hint", "") + h2.get("hint", "") + h3.get("hint", "")).lower()
check("Hidden test answer '1' not leaked as an explicit secret", "expected" not in all_hints_text)
check("Exception tracebacks not leaked in explanation", "traceback" not in exp_err.lower() and "file \"/task/code.py\"" not in exp_err.lower())


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
total = PASS + FAIL
print(f"\n{'═' * 55}")
print(f"  PHASE 4 RESULTS: {PASS}/{total} passed  |  {FAIL} failed")
print(f"{'═' * 55}\n")

sys.exit(0 if FAIL == 0 else 1)
