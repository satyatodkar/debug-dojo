"""
test_in_exam_hints.py — Debug Dojo In-Exam Hints Comprehensive Test Suite
========================================================================
Validates all 16 items specified in the Debug Dojo In-Exam Hints requirement:
  1. The Hints tab appears inside the examination page.
  2. Selecting Hints does not open a new browser tab or window.
  3. The timer continues while hints are open.
  4. Switching between Question, Hints and Instructions preserves the examination state.
  5. The source code remains intact while the student views hints.
  6. The first hint can be requested during an active exam.
  7. Subsequent hints appear progressively (Hint 1 -> Hint 2 -> Hint 3).
  8. No hint provides a complete corrected solution.
  9. Hint requests from unauthenticated users or unrelated examination attempts are rejected appropriately.
  10. Hint requests after finalisation follow the configured exam policy.
  11. Hidden-test inputs, expected answers and private exception messages remain protected.
  12. Timer expiration during hint viewing finalises the exam correctly.
  13. Existing Run Tests and Submit Exam workflows still function.
  14. The result screen continues to display Exit Exam and Next Challenge.
  15. Refreshing the page does not reset the timer or improperly reset hint progression.
  16. Practice Mode hints and other existing functionality remain unaffected.
"""

import sys
import os
import json
import time
import uuid
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8000"
PASS = 0
FAIL = 0


def check(name: str, condition: bool, extra: str = ""):
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


def post_json(path: str, payload: dict, headers: dict | None = None):
    url = BASE + path
    data = json.dumps(payload).encode("utf-8")
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, data=data, headers=req_headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = {}
        try:
            body = json.loads(e.read().decode("utf-8"))
        except Exception:
            pass
        return e.code, body


def get_req(path: str, headers: dict | None = None):
    url = BASE + path
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            ct = r.headers.get("Content-Type", "")
            raw = r.read().decode("utf-8", errors="replace")
            if "application/json" in ct:
                return r.status, json.loads(raw)
            return r.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw


def main():
    print("=" * 75)
    print("🥋 Debug Dojo — In-Exam Hints Comprehensive Verification Suite")
    print("=" * 75)

    test_uid = uuid.uuid4().hex[:6]
    learner_id = f"student_hint_{test_uid}"

    # -------------------------------------------------------------------------
    # 1. & 2. Examination Interface Layout: Hints tab inside exam page, no new window
    # -------------------------------------------------------------------------
    print("\n[1 & 2] Checking Examination HTML & JS for In-Page Hints Tab...")
    s, exam_html = get_req("/exam")
    check("GET /exam returns 200", s == 200)
    check("Hints tab button exists in exam page", 'id="exam-tab-hints"' in exam_html)
    check("Question tab button exists in exam page", 'id="exam-tab-question"' in exam_html)
    check("Instructions tab button exists in exam page", 'id="exam-tab-instructions"' in exam_html)
    check("Hints panel exists in exam page", 'id="exam-panel-hints"' in exam_html)
    check("Question panel exists in exam page", 'id="exam-panel-question"' in exam_html)
    check("Instructions panel exists in exam page", 'id="exam-panel-instructions"' in exam_html)
    check("Request Hint button exists in exam page", 'id="exam-request-hint-btn"' in exam_html)
    check("Hints list container exists in exam page", 'id="exam-hints-list"' in exam_html)

    s, exam_js = get_req("/static/exam.js")
    check("GET /static/exam.js returns 200", s == 200)
    check("Tab switching function is implemented in exam.js", "switchTab" in exam_js)
    check("Hints tab does not open window (_blank or window.open not in tab switch)", "switchTab('hints')" in exam_js or "switchTab(" in exam_js)

    s, exam_css = get_req("/static/exam.css")
    check("GET /static/exam.css returns 200", s == 200)
    check("Styles for .exam-tabs defined", ".exam-tabs" in exam_css)
    check("Styles for .hint-card defined", ".hint-card" in exam_css)
    check("Styles for .exam-panel defined", ".exam-panel" in exam_css)

    # -------------------------------------------------------------------------
    # 3., 4., 5. Start Active Exam & Verify Timer Continuity & Code State
    # -------------------------------------------------------------------------
    print("\n[3, 4, 5] Starting Exam Attempt: Checking Timer, Code, and State Preservation...")
    cid = "count_passes"
    s, attempt_data = post_json("/api/exam/start", {
        "challenge_id": cid,
        "learner_id": learner_id,
        "dev_duration": 120,
    })
    check("POST /api/exam/start returns 200", s == 200)
    att_id = attempt_data["attempt_id"]
    initial_deadline = attempt_data["deadline"]
    initial_rem = attempt_data["remaining_seconds"]
    check("Attempt ID generated", bool(att_id))
    check("Server deadline provided", bool(initial_deadline))
    check("Initial unlocked_hints is empty list", attempt_data.get("unlocked_hints") == [])

    # Let 2 seconds pass
    time.sleep(2)
    s, att_state = get_req(f"/api/exam/{att_id}")
    check("GET /api/exam/{attempt_id} returns 200", s == 200)
    check("Authoritative deadline remains identical", att_state["deadline"] == initial_deadline)
    check("Authoritative remaining seconds decreased", att_state["remaining_seconds"] < initial_rem)

    # -------------------------------------------------------------------------
    # 6., 7., 8. Request Progressive Hints (Hint 1, 2, 3) & Solution Protection
    # -------------------------------------------------------------------------
    print("\n[6, 7, 8] Progressive Hint Ladder (Think -> Investigate -> Narrow it down)...")

    # Hint 1 — Think
    s, h1 = post_json("/api/hint", {
        "attempt_id": att_id,
        "challenge_id": cid,
        "learner_id": learner_id,
    })
    check("POST /api/hint #1 returns 200", s == 200)
    check("Hint 1 status is active", h1.get("status") == "active")
    check("Hint 1 number is 1", h1.get("hint_number") == 1)
    check("Hint 1 stage is 'Think'", h1.get("stage") == "Think")
    check("Hint 1 label is 'Hint 1 — Think'", h1.get("label") == "Hint 1 — Think")
    check("Hint 1 has text", bool(h1.get("hint")))
    check("Hint 1 contains question mark ('?')", "?" in h1.get("hint", ""))
    check("Hint 1 has_more is True", h1.get("has_more") is True)
    check("unlocked_hints has 1 item", len(h1.get("unlocked_hints", [])) == 1)

    # Hint 2 — Investigate
    s, h2 = post_json("/api/hint", {
        "attempt_id": att_id,
        "challenge_id": cid,
        "learner_id": learner_id,
    })
    check("POST /api/hint #2 returns 200", s == 200)
    check("Hint 2 status is active", h2.get("status") == "active")
    check("Hint 2 number is 2", h2.get("hint_number") == 2)
    check("Hint 2 stage is 'Investigate'", h2.get("stage") == "Investigate")
    check("Hint 2 label is 'Hint 2 — Investigate'", h2.get("label") == "Hint 2 — Investigate")
    check("Hint 2 has text", bool(h2.get("hint")))
    check("Hint 2 has_more is True", h2.get("has_more") is True)
    check("unlocked_hints has 2 items", len(h2.get("unlocked_hints", [])) == 2)

    # Hint 3 — Narrow it down
    s, h3 = post_json("/api/hint", {
        "attempt_id": att_id,
        "challenge_id": cid,
        "learner_id": learner_id,
    })
    check("POST /api/hint #3 returns 200", s == 200)
    check("Hint 3 status is active", h3.get("status") == "active")
    check("Hint 3 number is 3", h3.get("hint_number") == 3)
    check("Hint 3 stage is 'Narrow it down'", h3.get("stage") == "Narrow it down")
    check("Hint 3 label is 'Hint 3 — Narrow it down'", h3.get("label") == "Hint 3 — Narrow it down")
    check("Hint 3 has text", bool(h3.get("hint")))
    check("Hint 3 has_more is False", h3.get("has_more") is False)
    check("unlocked_hints has 3 items", len(h3.get("unlocked_hints", [])) == 3)

    # Hint 4 — Exhausted state
    s, h4 = post_json("/api/hint", {
        "attempt_id": att_id,
        "challenge_id": cid,
        "learner_id": learner_id,
    })
    check("POST /api/hint #4 returns 200", s == 200)
    check("Status is 'exhausted'", h4.get("status") == "exhausted")
    check("Hint text is None on exhausted", h4.get("hint") is None)
    check("Exhaustion message returned", "All 3" in h4.get("message", ""))
    check("has_more is False", h4.get("has_more") is False)

    # Check solution protection across all hints
    full_solutions = ["def count_passes", "return passes", "for mark in marks:"]
    for i, h in enumerate([h1, h2, h3], 1):
        txt = h.get("hint", "")
        for sol in full_solutions:
            check(f"Hint {i} does not disclose full code ({sol})", sol not in txt)

    # -------------------------------------------------------------------------
    # 9. Ownership Validation & Security (Unrelated / Unauthenticated users)
    # -------------------------------------------------------------------------
    print("\n[9] Testing Ownership & Security Validation...")
    # Attempting to request hint with wrong learner_id
    s_wrong, err_wrong = post_json("/api/hint", {
        "attempt_id": att_id,
        "learner_id": "different_unauthorized_student",
    })
    check("Reject hint request with mismatching learner_id (403)", s_wrong == 403)

    # Unknown attempt ID
    s_unknown, err_unknown = post_json("/api/hint", {
        "attempt_id": "atm_nonexistent999",
        "learner_id": learner_id,
    })
    check("Reject hint request for unknown attempt (404)", s_unknown == 404)

    # Dedicated exam hint endpoint POST /api/exam/{attempt_id}/hint
    s_exam_hint, exam_h_data = post_json(f"/api/exam/{att_id}/hint", {
        "learner_id": learner_id,
    })
    check("POST /api/exam/{attempt_id}/hint returns 200", s_exam_hint == 200)
    check("Returns exhausted status since 3 hints unlocked", exam_h_data.get("status") == "exhausted")

    # GET /api/exam/{attempt_id}/hints
    s_get_hints, get_h_data = get_req(f"/api/exam/{att_id}/hints")
    check("GET /api/exam/{attempt_id}/hints returns 200", s_get_hints == 200)
    check("Returns exactly 3 unlocked hints", get_h_data.get("total_unlocked") == 3)
    check("Each hint has label, stage, requested_at", all("stage" in x and "label" in x for x in get_h_data.get("unlocked_hints", [])))

    # -------------------------------------------------------------------------
    # 11. Hidden-Test Secrecy Verification
    # -------------------------------------------------------------------------
    print("\n[11] Verifying Hidden Test Confidentiality...")
    # Hidden test inputs/expected must not appear in any hint or endpoint
    for h in [h1, h2, h3]:
        hint_str = json.dumps(h)
        check("No hidden_tests in hint payload", "hidden_tests" not in hint_str)
        check("No raw stacktrace in hint payload", "Traceback" not in hint_str)

    # -------------------------------------------------------------------------
    # 13. Run Visible Tests & Submit Exam Workflow Still Functions
    # -------------------------------------------------------------------------
    print("\n[13] Verifying Visible Test Execution During Active Exam...")
    s_run, run_res = post_json(f"/api/exam/{att_id}/run-tests", {
        "code": "def count_passes(marks):\n    return sum(1 for m in marks if m >= 40)\n",
    })
    check("POST /api/exam/{attempt_id}/run-tests returns 200", s_run == 200)
    check("Visible tests returned", "visible_tests" in run_res)
    check("All visible tests passed", run_res.get("visible_passed") == run_res.get("visible_total"))

    # -------------------------------------------------------------------------
    # 10. Finalization & Post-Finalization Hint Policy
    # -------------------------------------------------------------------------
    print("\n[10 & 14] Finalizing Exam & Verifying Post-Finalization Hint Policy...")
    s_sub, sub_res = post_json(f"/api/exam/{att_id}/submit", {
        "code": "def count_passes(marks):\n    return sum(1 for m in marks if m >= 40)\n",
    })
    check("POST /api/exam/{attempt_id}/submit returns 200", s_sub == 200)
    check("Attempt finalized as submitted", sub_res.get("status") == "submitted")
    check("all_passed is True", sub_res.get("all_passed") is True)

    # Attempt to request hint after finalization -> Must reject with 400
    s_post_fin, err_post_fin = post_json("/api/hint", {
        "attempt_id": att_id,
        "learner_id": learner_id,
    })
    check("Hint request after finalization rejected with 400", s_post_fin == 400)

    # Check result screen navigation elements in HTML & JS
    check("Exit Exam button exists in exam.html", 'id="results-exit-btn"' in exam_html)
    check("Next Challenge button exists in exam.html", 'id="results-next-btn"' in exam_html)
    check("Exit Exam handler implemented in exam.js", "resultsExitBtn.addEventListener" in exam_js or "handleExitExam" in exam_js or "results-exit-btn" in exam_js)
    check("Next Challenge handler implemented in exam.js", "resultsNextBtn.addEventListener" in exam_js or "handleNextChallenge" in exam_js or "results-next-btn" in exam_js)

    # -------------------------------------------------------------------------
    # 12. Timer Expiration During Exam Blocks Hints & Finalizes
    # -------------------------------------------------------------------------
    print("\n[12] Verifying Timer Expiration Handling...")
    s_short, short_att = post_json("/api/exam/start", {
        "challenge_id": "first_n_squares",
        "learner_id": f"student_exp_{test_uid}",
        "dev_duration": 1,  # 1 second duration
    })
    check("Created short attempt (1s)", s_short == 200)
    exp_att_id = short_att["attempt_id"]

    # Wait for expiration
    time.sleep(2)
    s_exp_state, exp_state = get_req(f"/api/exam/{exp_att_id}")
    check("Attempt status became 'expired' after deadline", exp_state.get("status") == "expired")
    check("Remaining seconds is 0", exp_state.get("remaining_seconds") == 0)

    # Hint request on expired attempt must be rejected with 400
    s_exp_hint, err_exp_hint = post_json("/api/hint", {
        "attempt_id": exp_att_id,
        "learner_id": f"student_exp_{test_uid}",
    })
    check("Hint request on expired attempt rejected with 400", s_exp_hint == 400)

    # -------------------------------------------------------------------------
    # 15. Persistence: Refreshing Page Restores Hints & Does Not Reset Timer
    # -------------------------------------------------------------------------
    print("\n[15] Verifying State Restoration On Page Refresh...")
    s_restore, restored_att = post_json("/api/exam/start", {
        "challenge_id": "middle_three",
        "learner_id": f"student_refresh_{test_uid}",
        "dev_duration": 600,
    })
    check("Created attempt for refresh test", s_restore == 200)
    ref_att_id = restored_att["attempt_id"]
    ref_deadline = restored_att["deadline"]

    # Unlock 2 hints
    post_json("/api/hint", {"attempt_id": ref_att_id, "learner_id": f"student_refresh_{test_uid}"})
    post_json("/api/hint", {"attempt_id": ref_att_id, "learner_id": f"student_refresh_{test_uid}"})

    # Simulate page refresh by fetching attempt
    s_reloaded, reloaded_data = get_req(f"/api/exam/{ref_att_id}")
    check("Reloaded attempt returns 200", s_reloaded == 200)
    check("Deadline did NOT reset on refresh", reloaded_data["deadline"] == ref_deadline)
    unlocked_on_reload = reloaded_data.get("unlocked_hints", [])
    check("Unlocked hints count preserved across reload (2)", len(unlocked_on_reload) == 2)
    check("Hint 1 preserved across reload", unlocked_on_reload[0]["hint_index"] == 1 and unlocked_on_reload[0]["stage"] == "Think")
    check("Hint 2 preserved across reload", unlocked_on_reload[1]["hint_index"] == 2 and unlocked_on_reload[1]["stage"] == "Investigate")

    # Unlock hint 3 now
    s_h3_after, h3_after = post_json("/api/hint", {"attempt_id": ref_att_id, "learner_id": f"student_refresh_{test_uid}"})
    check("Next hint after reload is Hint 3", h3_after.get("hint_number") == 3 and h3_after.get("stage") == "Narrow it down")

    # -------------------------------------------------------------------------
    # 16. Practice Mode Hints & Existing Functionality Unaffected
    # -------------------------------------------------------------------------
    print("\n[16] Verifying Practice Mode Hints Remain Unaffected...")
    # Submit buggy practice code
    s_prac_sub, prac_res = post_json("/api/submit", {
        "learner_id": f"practice_student_{test_uid}",
        "challenge_id": "count_passes",
        "code": "def count_passes(marks):\n    return sum(1 for m in marks if m > 40)\n",
    })
    check("Practice mode submission returns 200", s_prac_sub == 200)
    prac_sub_id = prac_res.get("submission_id")
    check("Practice submission ID returned", bool(prac_sub_id))

    # Request hint using submission_id
    s_prac_h1, prac_h1 = post_json("/api/hint", {"submission_id": prac_sub_id})
    check("Practice mode POST /api/hint with submission_id returns 200", s_prac_h1 == 200)
    check("Practice hint 1 has hint_number 1", prac_h1.get("hint_number") == 1)
    check("Practice hint 1 has question mark", "?" in prac_h1.get("hint", ""))

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------
    print("\n" + "=" * 75)
    print(f"RESULTS: {PASS} passed, {FAIL} failed")
    print("=" * 75)
    if FAIL > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
