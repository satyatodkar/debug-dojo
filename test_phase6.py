"""
test_phase6.py  —  Debug Dojo Phase 6 UI & Workflow Integration Test Suite
===========================================================================
Validates:
  1. Frontend homepage (GET /) serves clean HTML with navigation system (Workspace, My Progress, Challenges).
  2. Static assets (style.css, app.js) load with 200 OK.
  3. No sensitive hidden-test inputs or answers are leaked in static files (HTML, CSS, JS).
  4. Work preservation: JS implements code caching and Tab key indentation.
  5. Submission duplicate prevention: JS implements submission lock and loading states.
  6. Infrastructure error classification: system/Docker errors are distinguished from student bugs.
  7. Reduced motion: CSS respects @media (prefers-reduced-motion: reduce).
  8. Accessibility: keyboard focus outlines and ARIA attributes present.
  9. Backend integration: GET /api/health, GET /api/challenges, and GET /api/learner/student1 all functional.
"""

import sys
import os
import json
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8000"
PASS = 0
FAIL = 0


def get_req(path):
    url = BASE + path
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")


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


def main():
    print("=" * 70)
    print("🥋 Debug Dojo Phase 6 Test Suite")
    print("=" * 70)

    # 1. Homepage & Navigation
    print("\n--- 1. Homepage & Navigation System ---")
    st, html = get_req("/")
    check("GET / serves 200 OK", st == 200)
    check("Page title contains 'Debug Dojo'", "Debug Dojo" in html)
    check("Workspace navigation button present", 'id="nav-workspace-btn"' in html)
    check("My Progress navigation button present", 'id="nav-dashboard-btn"' in html)
    check("Challenges mobile toggle button present", 'id="nav-mobile-challenges-btn"' in html)
    check("Health check badge element present", 'id="health-badge"' in html)
    check("Search filter input present", 'id="challenge-search"' in html)
    check("Reset code button present", 'id="reset-code-btn"' in html)
    check("Starter code editor present", 'id="starter-code"' in html)
    check("Run Tests button present", 'id="run-btn"' in html)
    check("Progressive hints section present", 'id="hints-section"' in html)
    check("Learner dashboard present", 'id="learner-dashboard"' in html)

    # 2. Static CSS Stylesheet
    print("\n--- 2. Styling, Monospace & Reduced Motion ---")
    st, css = get_req("/static/style.css")
    check("GET /static/style.css serves 200 OK", st == 200)
    check("Monospace font family defined for editor", "--font-mono" in css and "monospace" in css)
    check("Focus-visible outline defined for accessibility", ":focus-visible" in css)
    check("Reduced motion media query present", "prefers-reduced-motion" in css)
    check("Infrastructure error styling present", ".infra-error" in css)
    check("Responsive breakpoints defined", "@media" in css)

    # 3. Static JS Logic & Work Preservation
    print("\n--- 3. JavaScript Logic & Work Preservation ---")
    st, js = get_req("/static/app.js")
    check("GET /static/app.js serves 200 OK", st == 200)
    check("Code caching cache implemented for work preservation", "learnerCodeCache" in js)
    check("Tab key indentation handling implemented", "Tab" in js and "selectionStart" in js)
    check("Duplicate submission guard implemented", "isSubmitting" in js)
    check("Reset code functionality implemented", "resetActiveChallengeCode" in js)
    check("Live challenge filtering implemented", "filterChallenges" in js)
    check("View switching implemented", "switchView" in js)
    check("Learner dashboard dynamic loading implemented", "loadLearnerDashboard" in js)

    # 4. Hidden Test Confidentiality
    print("\n--- 4. Confidentiality of Hidden Tests in Frontend ---")
    check("Hidden test answer 'NOHTYP' not in HTML", "NOHTYP" not in html)
    check("Hidden test answer 'NOHTYP' not in JS", "NOHTYP" not in js)
    check("Hidden test answer '321cba' not in HTML", "321cba" not in html)
    check("Hidden test answer '321cba' not in JS", "321cba" not in js)
    check("Hidden test answer 'aaaaaa' not in HTML", "aaaaaa" not in html)
    check("Hidden test answer 'aaaaaa' not in JS", "aaaaaa" not in js)

    # 5. Live Backend Endpoints
    print("\n--- 5. Live Backend Endpoints Integration ---")
    st, health_raw = get_req("/api/health")
    check("GET /api/health is 200 OK", st == 200)
    health_json = json.loads(health_raw)
    check("Health status is 'ok'", health_json.get("status") == "ok")

    st, challenges_raw = get_req("/api/challenges")
    check("GET /api/challenges is 200 OK", st == 200)
    ch_list = json.loads(challenges_raw)
    check("Returns exactly 10 challenges", len(ch_list) == 10)

    st, detail_raw = get_req("/api/challenges/count_passes")
    check("GET /api/challenges/count_passes is 200 OK", st == 200)
    detail_json = json.loads(detail_raw)
    check("Visible tests present", len(detail_json.get("visible_tests", [])) >= 3)
    check("Hidden tests omitted from public API response", "hidden_tests" not in detail_json)

    st, learner_raw = get_req("/api/learner/student1")
    check("GET /api/learner/student1 is 200 OK", st == 200)
    learner_json = json.loads(learner_raw)
    check("Learner ID matches", learner_json.get("learner_id") == "student1")
    check("Mastery dictionary has all 6 concepts", len(learner_json.get("mastery", {})) == 6)
    check("Recommended challenge present", learner_json.get("next_recommended_challenge") is not None)

    # Summary
    print("\n" + "=" * 70)
    print(f"Results: {PASS} passed, {FAIL} failed")
    print("=" * 70)
    if FAIL > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
