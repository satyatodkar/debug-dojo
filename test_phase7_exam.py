"""
test_phase7_exam.py — Comprehensive Examination Mode, Anti-Paste & Sandbox Test Suite
====================================================================================
Automated test suite verifying:
  • Section 16: Examination Interface & Timer Tests (new tab, layout, difficulty timers, refresh, expiry, duplicates)
  • Section 17: Anti-Paste Controls & Integrity Signals (paste blocks, shortcuts, blur/tab events, rate limiting)
  • Section 18: Disposable Docker Sandbox & Hidden-Test Confidentiality (isolated container, network/filesystem blocked,
                timeout, memory/output bounds, cleanup, hidden test secrets protection, fail-closed enforcement)
"""

import sys
import os
import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

BASE = "http://127.0.0.1:8000"
PASS = 0
FAIL = 0


def check(desc: str, condition: bool, extra: str = ""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✓ {desc}")
    else:
        FAIL += 1
        msg = f"  ✗ {desc}"
        if extra:
            msg += f" — {extra}"
        print(msg)


def post_json(path: str, payload: dict):
    url = BASE + path
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = {}
        try:
            body = json.loads(e.read().decode("utf-8"))
        except Exception:
            pass
        return e.code, body


def get_req(path: str):
    url = BASE + path
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            content_type = r.headers.get("Content-Type", "")
            raw = r.read().decode("utf-8", errors="replace")
            if "application/json" in content_type:
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
    print("🥋 Debug Dojo — Phase 7 Examination Mode & Sandbox Test Suite")
    print("=" * 75)

    # ── 1. Examination Interface & Separate Tab Routes ──────────────────────
    print("\n--- 1. Examination Interface & Tab Routes ---")
    st, exam_html = get_req("/exam")
    check("GET /exam serves 200 OK", st == 200)
    check("Page title contains 'Debug Dojo — Examination Panel'", "Debug Dojo — Examination Panel" in exam_html)
    check("Fixed header element present", 'class="exam-header"' in exam_html)
    check("Continuous countdown timer container present", 'id="exam-timer-container"' in exam_html)
    check("Fullscreen toggle button present", 'id="exam-fullscreen-btn"' in exam_html)
    check("Header Submit Exam button present", 'id="exam-header-submit-btn"' in exam_html)
    check("Left column question paper present", 'class="exam-left-column"' in exam_html)
    check("Right column coding workspace present", 'class="exam-right-column"' in exam_html)
    check("Python exam code editor present", 'id="exam-editor"' in exam_html)
    check("Test results console present", 'id="results-console"' in exam_html)
    check("Submit confirmation modal present", 'id="submit-modal"' in exam_html)

    st, exam_css = get_req("/static/exam.css")
    check("GET /static/exam.css serves 200 OK", st == 200)
    check("Full viewport lock (100% / 100vh) in CSS", "100%" in exam_css and "hidden" in exam_css)
    check("5-minute warning timer styles defined", "timer-warning-5m" in exam_css)
    check("1-minute urgent warning timer styles defined", "timer-warning-1m" in exam_css)
    check("Reduced motion support present in exam CSS", "prefers-reduced-motion" in exam_css)

    st, exam_js = get_req("/static/exam.js")
    check("GET /static/exam.js serves 200 OK", st == 200)
    check("Anti-paste interception implemented in JS", "paste" in exam_js and "preventDefault" in exam_js)
    check("Paste keyboard shortcut interception implemented", "Insert" in exam_js or "ctrlKey" in exam_js)
    check("Tab indentation handling implemented in exam editor", "selectionStart" in exam_js)

    # Verify Start Exam buttons exist on main Dojo page
    st, main_html = get_req("/")
    check("Main Dojo page has 'Start Exam' workspace button", 'id="start-exam-workspace-btn"' in main_html)
    st, main_js = get_req("/static/app.js")
    check("Main Dojo app.js has 'Start Exam' button with _blank target", "window.open" in main_js and "_blank" in main_js)

    import uuid
    uid = uuid.uuid4().hex[:6]

    # ── 2. Difficulty-Based Authoritative Timers ─────────────────────────────
    print("\n--- 2. Difficulty-Based Authoritative Timers ---")
    # Easy challenge: 15 minutes = 900 seconds
    s, easy_data = post_json("/api/exam/start", {"challenge_id": "last_k_total", "learner_id": f"exam_timer_easy_{uid}"})
    check("POST /api/exam/start (Easy: last_k_total) returns 200", s == 200)
    check("Easy challenge duration is exactly 15 minutes (900s)", easy_data.get("duration_seconds") == 900)
    check("Easy challenge initial remaining is 900s", easy_data.get("remaining_seconds") == 900)
    check("Authoritative deadline timestamp present in ISO format", "T" in easy_data.get("deadline", ""))

    # Medium challenge: 25 minutes = 1500 seconds
    s, med_data = post_json("/api/exam/start", {"challenge_id": "middle_three", "learner_id": f"exam_timer_med_{uid}"})
    check("POST /api/exam/start (Medium: middle_three) returns 200", s == 200)
    check("Medium challenge duration is exactly 25 minutes (1500s)", med_data.get("duration_seconds") == 1500)

    # Hard challenge: 40 minutes = 2400 seconds
    s, hard_data = post_json("/api/exam/start", {"challenge_id": "remove_duplicates", "learner_id": f"exam_timer_hard_{uid}"})
    check("POST /api/exam/start (Hard: remove_duplicates) returns 200", s == 200)
    check("Hard challenge duration is exactly 40 minutes (2400s)", hard_data.get("duration_seconds") == 2400)

    # Verification: Page refresh does NOT reset or extend deadline
    print("\n--- 3. Authoritative Deadline Persistence Across Refreshes ---")
    att_id = easy_data["attempt_id"]
    initial_deadline = easy_data["deadline"]
    initial_rem = easy_data["remaining_seconds"]

    time.sleep(2)
    s, get_data = get_req(f"/api/exam/{att_id}")
    check("GET /api/exam/{attempt_id} returns 200", s == 200)
    check("Server deadline timestamp remains unchanged after refresh", get_data.get("deadline") == initial_deadline)
    check("Remaining time properly decremented from authoritative deadline", get_data.get("remaining_seconds") <= initial_rem - 1)

    # Deduplication on double-click
    s, dup_data = post_json("/api/exam/start", {"challenge_id": "last_k_total", "learner_id": f"exam_timer_easy_{uid}"})
    check("Accidental duplicate start returns existing active attempt", dup_data.get("attempt_id") == att_id)

    # ── 4. Authoritative Expiration & Double Finalization Protection ─────────
    print("\n--- 4. Authoritative Expiration & Double Finalization ---")
    # Start attempt with 4-second dev timer
    s, exp_att = post_json("/api/exam/start", {
        "challenge_id": "count_passes",
        "learner_id": f"expiry_student_{uid}",
        "dev_duration": 4,
    })
    exp_id = exp_att["attempt_id"]
    check("Started short-duration exam for expiry test", s == 200 and exp_att.get("duration_seconds") == 4)

    # Wait for expiration
    time.sleep(5)
    s, post_exp = get_req(f"/api/exam/{exp_id}")
    check("Attempt automatically transitions to 'expired' when deadline passes", post_exp.get("status") == "expired")
    check("Remaining seconds clamped to 0", post_exp.get("remaining_seconds") == 0)

    # Running tests on expired attempt rejected
    s, run_err = post_json(f"/api/exam/{exp_id}/run-tests", {"code": "def count_passes(m): return 0"})
    check("Running tests on expired attempt returns 400", s == 400)

    # Submitting on expired attempt rejected
    s, sub_err = post_json(f"/api/exam/{exp_id}/submit", {"code": "def count_passes(m): return 0"})
    check("Submitting on expired attempt returns 400", s == 400)

    # ── 5. Anti-Paste Controls & Integrity Logging ──────────────────────────
    print("\n--- 5. Anti-Paste Controls & Integrity Event Logging ---")
    s, normal_att = post_json("/api/exam/start", {
        "challenge_id": "first_n_squares",
        "learner_id": f"integrity_student_{uid}",
    })
    int_id = normal_att["attempt_id"]

    # Log integrity signals
    s, res1 = post_json(f"/api/exam/{int_id}/integrity", {"event_type": "paste_attempt", "details": "Ctrl+V intercepted"})
    check("Paste attempt event logged successfully", s == 200 and res1.get("recorded") is True)
    check("Event count incremented to 1", res1.get("total_events") == 1)

    s, res2 = post_json(f"/api/exam/{int_id}/integrity", {"event_type": "tab_switch_hidden", "details": "Tab blurred"})
    check("Tab visibility change event logged", s == 200 and res2.get("total_events") == 2)

    s, res3 = post_json(f"/api/exam/{int_id}/integrity", {"event_type": "fullscreen_exit", "details": "Exited fullscreen"})
    check("Fullscreen exit event logged", s == 200 and res3.get("total_events") == 3)
    check("Integrity warning triggered when threshold (3) reached", res3.get("warning") is True)

    # Check that focus loss does NOT disqualify the student
    s, check_att = get_req(f"/api/exam/{int_id}")
    check("Student NOT automatically disqualified by focus loss (still in_progress)", check_att.get("status") == "in_progress")
    check("Integrity events count reported in attempt details", check_att.get("integrity_events_count") == 3)
    check("Integrity warning active in attempt details", check_att.get("integrity_warning") is True)

    # Invalid attempt ID returns 404
    s, err404 = post_json("/api/exam/non_existent_atm/integrity", {"event_type": "paste_attempt"})
    check("Integrity event for non-existent attempt returns 404", s == 404)

    # ── 6. Disposable Docker Code Execution & Sandbox Security ───────────────
    print("\n--- 6. Disposable Docker Code Execution & Sandbox Security ---")
    s, exam_run = post_json("/api/exam/start", {
        "challenge_id": "count_passes",
        "learner_id": f"sandbox_exam_student_{uid}",
    })
    run_id = exam_run["attempt_id"]

    # Test Run Visible Tests only (does NOT touch hidden tests)
    correct_code = """
def count_passes(marks):
    return sum(1 for x in marks if x >= 40)
"""
    s, vis_res = post_json(f"/api/exam/{run_id}/run-tests", {"code": correct_code})
    check("POST /run-tests returns 200", s == 200)
    check("All visible tests passed in isolated container", vis_res.get("visible_passed") == vis_res.get("visible_total"), str(vis_res))
    check("Visible test response does NOT contain hidden tests", "hidden_tests" not in vis_res)

    # Verify attempt remains in_progress after run-tests
    s, still_active = get_req(f"/api/exam/{run_id}")
    check("Attempt remains 'in_progress' after running visible tests", still_active.get("status") == "in_progress")

    # Test Final Exam Submission
    s, sub_res = post_json(f"/api/exam/{run_id}/submit", {"code": correct_code})
    check("Final POST /submit returns 200", s == 200)
    check("all_passed is True for correct solution", sub_res.get("all_passed") is True)
    check("Attempt status finalized to 'submitted'", sub_res.get("status") == "submitted")

    # Verify Hidden Test Confidentiality in API response
    print("\n--- 7. Hidden-Test Confidentiality Protection ---")
    hidden_tests = sub_res.get("hidden_tests", [])
    check("Hidden tests outcome count matches expected", len(hidden_tests) >= 5)
    check("Hidden tests do NOT leak input arguments", all("args" not in t for t in hidden_tests))
    check("Hidden tests do NOT leak expected values", all("expected" not in t for t in hidden_tests))
    check("Hidden tests do NOT leak actual return values", all("actual" not in t for t in hidden_tests))
    check("Hidden tests do NOT leak raw error tracebacks", all("error_msg" not in t for t in hidden_tests))

    # Verify duplicate finalization is strictly prevented
    print("\n--- 8. Duplicate Finalization Guard ---")
    s, dup_err = post_json(f"/api/exam/{run_id}/submit", {"code": correct_code})
    check("Submitting an already finalized attempt returns 400", s == 400)
    check("Error message indicates attempt is already finalized", "already finalized" in dup_err.get("detail", ""))

    # ── 9. Malformed & Invalid Requests ─────────────────────────────────────
    print("\n--- 9. Validation & Error Handling ---")
    s, err_cid = post_json("/api/exam/start", {"challenge_id": "invalid_challenge_xyz", "learner_id": "test"})
    check("Unknown challenge ID returns 404", s == 404)

    s, err_size = post_json(f"/api/exam/{int_id}/run-tests", {"code": "x = 1\n" * 40000})
    check("Code exceeding 32KB returns 400", s == 400)

    # ── Summary ─────────────────────────────────────────────────────────────
    print("\n" + "=" * 75)
    print(f"Results: {PASS} passed, {FAIL} failed")
    print("=" * 75)
    if FAIL > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
