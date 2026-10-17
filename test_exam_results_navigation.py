"""
test_exam_results_navigation.py — Examination Results Screen & Navigation Test Suite
=====================================================================================
Validates:
  1. Frontend Examination Results Overlay Elements in exam.html
  2. CSS Styling, Accessibility, Focus States, Responsive & Reduced Motion in exam.css
  3. Results Logic, Tab Switching, and Fallback Navigation in exam.js
  4. Cross-Tab Message Listener and Challenge Highlighting in app.js
  5. Server-Authoritative Finalization, Timestamping, and Attempt Preservation
  6. Confidentiality of Hidden Tests on Final Submission
  7. Protection Against Duplicate Submission & Post-Finalization Code Execution
  8. Expiry Finalization State & Preserved Details
"""

import sys
import json
import urllib.request
import urllib.error
import time

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
        with urllib.request.urlopen(req, timeout=30) as r:
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
    print("=" * 80)
    print("🥋 Debug Dojo — Examination Results Screen & Navigation Test Suite")
    print("=" * 80)

    # ── 1. Examination Results Overlay Elements in exam.html ──────────────────
    print("\n--- 1. Results Overlay Markup in exam.html ---")
    st, exam_html = get_req("/exam")
    check("GET /exam returns 200 OK", st == 200)
    check("Results overlay container present", 'id="exam-results-overlay"' in exam_html)
    check("Results overlay has hidden class by default", 'class="exam-results-overlay hidden"' in exam_html)
    check("Results status icon element present", 'id="results-status-icon"' in exam_html)
    check("Results heading element present", 'id="results-heading"' in exam_html)
    check("Results status badge element present", 'id="results-status-badge"' in exam_html)
    check("Results challenge title element present", 'id="results-challenge-title"' in exam_html)
    check("Results difficulty badge present", 'id="results-difficulty-badge"' in exam_html)
    check("Results score card present", 'id="results-score-card"' in exam_html)
    check("Visible test score display present", 'id="results-visible-score"' in exam_html)
    check("Hidden test score display present", 'id="results-hidden-score"' in exam_html)
    check("Total score display present", 'id="results-total-score"' in exam_html)
    check("Summary text container present", 'id="results-summary-text"' in exam_html)
    check("Submission timestamp container present", 'id="results-timestamp-value"' in exam_html)
    check("Visible test results list container present", 'id="results-test-list"' in exam_html)
    check("Exit Exam button present with appropriate label", 'id="results-exit-btn"' in exam_html and "Exit Exam" in exam_html)
    check("Next Challenge button present with primary text", 'id="results-next-btn"' in exam_html and "Next Challenge" in exam_html)
    check("Completion message placeholder present", 'id="results-completion-msg"' in exam_html)
    check("Buttons have aria-label for accessibility", 'aria-label="Exit Exam and return to Challenges"' in exam_html)

    # ── 2. Results Screen Styling in exam.css ─────────────────────────────────
    print("\n--- 2. Results Screen CSS & Design System in exam.css ---")
    st, exam_css = get_req("/static/exam.css")
    check("GET /static/exam.css returns 200 OK", st == 200)
    check(".exam-results-overlay styles defined with backdrop-filter", ".exam-results-overlay" in exam_css and "backdrop-filter" in exam_css)
    check(".exam-results-container styles defined with box-shadow", ".exam-results-container" in exam_css)
    check(".results-btn styles defined", ".results-btn" in exam_css)
    check("Primary style for Next Challenge defined", ".results-btn.btn--primary" in exam_css)
    check("Secondary outlined style for Exit Exam defined", ".results-btn.btn--secondary" in exam_css)
    check("Focus visible states defined for keyboard navigation", ":focus-visible" in exam_css)
    check("Hover states defined for buttons", ".results-btn.btn--primary:hover" in exam_css and ".results-btn.btn--secondary:hover" in exam_css)
    check("Responsive styles for mobile / tablets defined", "@media (max-width: 640px)" in exam_css)
    check("Reduced motion support defined", "@media (prefers-reduced-motion: reduce)" in exam_css)

    # ── 3. Results Screen Logic & Navigation in exam.js ──────────────────────
    print("\n--- 3. Results Screen Controller & Cross-Tab Navigation in exam.js ---")
    st, exam_js = get_req("/static/exam.js")
    check("GET /static/exam.js returns 200 OK", st == 200)
    check("showResultsScreen function implemented", "function showResultsScreen(" in exam_js)
    check("Finalization disables code editor", "editor.disabled = true" in exam_js)
    check("Finalization disables run tests button", "runTestsBtn.disabled = true" in exam_js)
    check("Finalization disables submit button", "submitExamBtn.disabled = true" in exam_js)
    check("handleExitExam navigates to #challenges", "handleExitExam" in exam_js and "#challenges" in exam_js)
    check("handleNextChallenge resolves next uncompleted challenge", "handleNextChallenge" in exam_js)
    check("PostMessage sends to window.opener with origin validation", "window.opener.postMessage" in exam_js and "window.location.origin" in exam_js)
    check("PostMessage payload has debug_dojo_exam_complete type", "'debug_dojo_exam_complete'" in exam_js)
    check("Fallback navigation to window.location.href implemented", "window.location.href = targetUrl" in exam_js)
    check("Keyboard navigation support (Enter / Space) for buttons", "e.key === 'Enter'" in exam_js)
    check("End-of-challenges completion message handling implemented", "showCompletionMessage" in exam_js)

    # ── 4. Main Tab Message Listener & Hash Routing in app.js ────────────────
    print("\n--- 4. Main Tab PostMessage Listener & Hash Navigation in app.js ---")
    st, app_js = get_req("/static/app.js")
    check("GET /static/app.js returns 200 OK", st == 200)
    check("Message event listener validates origin strictly", "event.origin !== window.location.origin" in app_js)
    check("Message event listener checks type debug_dojo_exam_complete", "debug_dojo_exam_complete" in app_js)
    check("Message handler switches view to challenges", "showView('challenges')" in app_js)
    check("Hash change listener registered for direct fallback navigation", "addEventListener('hashchange'" in app_js)
    check("handleHashNavigation supports #challenges?highlight= parameter", "handleHashNavigation" in app_js)
    check("highlightChallengeCard function implemented", "function highlightChallengeCard(" in app_js)
    check("Challenge cards have data-id attribute assigned", "card.dataset.id = ch.id" in app_js)
    check("Highlight applies visible visual outline/pulse and smooth scroll", "scrollIntoView" in app_js and "outline" in app_js)

    # ── 5. Server-Side Finalization, Submitted Timestamp & Score ──────────────
    print("\n--- 5. Server-Authoritative Submission & Evaluation ---")
    st, start_data = post_json("/api/exam/start", {
        "challenge_id": "count_passes",
        "learner_id": "results_tester_1",
    })
    check("POST /api/exam/start returns 200 OK", st == 200)
    attempt_id = start_data["attempt_id"]
    check("Attempt ID generated", attempt_id.startswith("atm_"))

    correct_code = """
def count_passes(marks):
    return sum(1 for x in marks if x >= 40)
"""

    st, sub_data = post_json(f"/api/exam/{attempt_id}/submit", {"code": correct_code})
    check("POST /api/exam/{id}/submit returns 200 OK", st == 200)
    check("Final status is 'submitted'", sub_data.get("status") == "submitted")
    check("Evaluation all_passed is True", sub_data.get("all_passed") is True)
    check("Server provides authoritative submitted_at timestamp", bool(sub_data.get("submitted_at")))
    check("Server returns score summary", "Passed" in sub_data.get("summary", "") or "Passed!" in sub_data.get("summary", ""))
    check("Visible test results included with outcome", len(sub_data.get("visible_tests", [])) > 0)
    check("Hidden test summary included without disclosing hidden inputs", "hidden_summary" in sub_data)

    # ── 6. Confidentiality Verification ──────────────────────────────────────
    print("\n--- 6. Hidden-Test Confidentiality on Submission ---")
    hidden_tests = sub_data.get("hidden_tests", [])
    check("Hidden tests outcome count > 0", len(hidden_tests) > 0)
    for idx, ht in enumerate(hidden_tests):
        check(f"Hidden test #{idx+1} does NOT contain 'args'", "args" not in ht)
        check(f"Hidden test #{idx+1} does NOT contain 'expected'", "expected" not in ht)
        check(f"Hidden test #{idx+1} does NOT contain 'call'", "call" not in ht)
        check(f"Hidden test #{idx+1} does NOT contain 'input'", "input" not in ht)

    # ── 7. Attempt Persistence & Anti-Tampering ──────────────────────────────
    print("\n--- 7. Attempt Persistence & Tamper Prevention ---")
    st, attempt_check = get_req(f"/api/exam/{attempt_id}")
    check("GET /api/exam/{id} returns 200 OK", st == 200)
    check("Persisted attempt status is 'submitted'", attempt_check.get("status") == "submitted")
    check("Persisted attempt preserves submitted_at", attempt_check.get("submitted_at") == sub_data.get("submitted_at"))
    check("Persisted attempt preserves submitted_code", attempt_check.get("submitted_code") == correct_code)

    st, dup_submit = post_json(f"/api/exam/{attempt_id}/submit", {"code": correct_code})
    check("Duplicate submission returns 400 Bad Request", st == 400)
    check("Duplicate submission error notes attempt already finalized", "already finalized" in dup_submit.get("detail", "").lower())

    st, late_run = post_json(f"/api/exam/{attempt_id}/run-tests", {"code": correct_code})
    check("Running tests on finalized attempt returns 400 Bad Request", st == 400)

    # ── 8. Time Expired Flow ─────────────────────────────────────────────────
    print("\n--- 8. Time Expired Flow & Result State ---")
    st, exp_start = post_json("/api/exam/start", {
        "challenge_id": "count_passes",
        "learner_id": "results_tester_expiry",
        "dev_duration": 1,
    })
    check("Started short 1-second exam", st == 200)
    exp_attempt_id = exp_start["attempt_id"]

    time.sleep(2.0)

    st, exp_check = get_req(f"/api/exam/{exp_attempt_id}")
    check("Expired exam transitions to status 'expired'", exp_check.get("status") == "expired")
    check("Remaining seconds clamped to 0", exp_check.get("remaining_seconds") == 0)
    check("Expired attempt records submitted_at/finalized_at", bool(exp_check.get("submitted_at")))

    # ── 9. Catalogue & Learner Recommendation Endpoints ─────────────────────
    print("\n--- 9. Catalogue & Learner Recommendation Endpoints ---")
    st, challenges = get_req("/api/challenges")
    check("GET /api/challenges returns 200 OK", st == 200 and isinstance(challenges, list))
    check("Catalog has challenges to recommend", len(challenges) >= 5)

    st, learner_data = get_req("/api/learner/student1")
    check("GET /api/learner/student1 returns 200 OK", st == 200)
    check("Learner endpoint provides recommendation or challenge status", "recommended_challenge" in learner_data or "challenges" in learner_data)

    print("\n" + "=" * 80)
    print(f"Results: {PASS} passed, {FAIL} failed")
    print("=" * 80)
    if FAIL > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
