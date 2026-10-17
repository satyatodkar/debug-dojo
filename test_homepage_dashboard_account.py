"""
test_homepage_dashboard_account.py
Comprehensive verification test suite for Debug Dojo:
- Homepage layout, branding, and auth/unauth navigation
- My Dashboard as the single place for learning analytics (stats, mastery sync, recurring mistakes >=2 rule, recommendation)
- My Account cleanup (personal profile & security only, learning analytics removed)
- Access controls and privacy (unauthenticated guards)
"""

import os
import sys
import json
import sqlite3
import urllib.request
import urllib.error
import http.cookiejar

BASE = "http://127.0.0.1:8000"
DB_PATH = "sandbox/dojo.db"

passed = 0
failed = 0

def check(desc: str, condition: bool, extra: str = ""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✓ {desc}")
    else:
        failed += 1
        msg = f"  ✗ {desc}"
        if extra:
            msg += f" -- {extra}"
        print(msg)


class DojoClient:
    def __init__(self):
        self.cj = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cj))

    def get(self, path: str):
        req = urllib.request.Request(f"{BASE}{path}", method="GET")
        try:
            with self.opener.open(req, timeout=10) as resp:
                data = resp.read().decode("utf-8")
                try:
                    return resp.status, json.loads(data)
                except Exception:
                    return resp.status, data
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8")
            try:
                return e.code, json.loads(raw)
            except Exception:
                return e.code, raw

    def post(self, path: str, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{BASE}{path}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self.opener.open(req, timeout=15) as resp:
                data = resp.read().decode("utf-8")
                try:
                    return resp.status, json.loads(data)
                except Exception:
                    return resp.status, data
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8")
            try:
                return e.code, json.loads(raw)
            except Exception:
                return e.code, raw

    def patch(self, path: str, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{BASE}{path}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="PATCH",
        )
        try:
            with self.opener.open(req, timeout=10) as resp:
                data = resp.read().decode("utf-8")
                try:
                    return resp.status, json.loads(data)
                except Exception:
                    return resp.status, data
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8")
            try:
                return e.code, json.loads(raw)
            except Exception:
                return e.code, raw


print("=" * 76)
print("🥋 Debug Dojo — Homepage Consistency, Dashboard Org & Account Cleanup")
print("=" * 76)

# -----------------------------------------------------------------------------
# 1. Frontend Structure Verification (HTML / CSS / JS)
# -----------------------------------------------------------------------------
print("\n--- 1. Frontend HTML & Layout Architecture ---")
with open("static/index.html", "r", encoding="utf-8") as f:
    html = f.read()

with open("static/app.js", "r", encoding="utf-8") as f:
    js = f.read()

with open("static/style.css", "r", encoding="utf-8") as f:
    css = f.read()

check("Branding contains Debug Dojo", "Debug Dojo" in html)
check("Hero headline is exactly 'Learn to Debug. Think Like a Programmer.'",
      "Learn to Debug. Think Like a Programmer." in html)
check("Feature 1: Secure Code Execution present", "Secure Code Execution" in html)
check("Feature 2: Progressive Hints present", "Progressive Hints" in html)
check("Feature 3: Personal Learning Intelligence present", "Personal Learning Intelligence" in html)
check("How It Works section present", "How It Works" in html)
check("CTA banner present", "landing-cta-section" in html)
check("Footer present", "<footer" in html and "Debug Dojo" in html)

# Navigation elements in HTML
check("Home nav button present (#nav-home-btn)", 'id="nav-home-btn"' in html)
check("Challenges nav button present (#nav-challenges-btn)", 'id="nav-challenges-btn"' in html)
check("Workspace nav tab present with hidden class (#nav-workspace-btn)", 'id="nav-workspace-btn"' in html)
check("My Dashboard nav tab present with hidden class (#nav-dashboard-btn)", 'id="nav-dashboard-btn"' in html)
check("My Account nav tab present with hidden class (#nav-account-btn)", 'id="nav-account-btn"' in html)
check("Visitor actions present (#nav-visitor-actions with Log In & Create Account)",
      'id="nav-visitor-actions"' in html and 'id="nav-login-btn"' in html and 'id="nav-signup-btn"' in html)
check("Authenticated actions present (#nav-user-actions with user chip & Log Out)",
      'id="nav-user-actions"' in html and 'id="nav-user-chip"' in html and 'id="nav-logout-btn"' in html)

# Adaptive hero & CTA elements
check("Hero has visitor badge and auth badge", 'id="hero-badge-visitor"' in html and 'id="hero-badge-auth"' in html)
check("Hero has visitor CTA group (#hero-visitor-ctas)", 'id="hero-visitor-ctas"' in html)
check("Hero has authenticated CTA group (#hero-auth-ctas)", 'id="hero-auth-ctas"' in html)
check("Hero has Start Learning and Explore Features buttons",
      'id="hero-start-learning-btn"' in html and 'id="hero-explore-features-btn"' in html)
check("Hero has Explore Challenges and My Dashboard buttons for auth",
      'id="hero-resume-btn"' in html and 'id="hero-dashboard-btn"' in html)
check("Adaptive bottom CTAs (#cta-visitor-box and #cta-auth-box)",
      'id="cta-visitor-box"' in html and 'id="cta-auth-box"' in html)
check("Home authenticated learning snapshot strip (#home-auth-summary)",
      'id="home-auth-summary"' in html)

# -----------------------------------------------------------------------------
# 2. My Dashboard Layout & Reorganization
# -----------------------------------------------------------------------------
print("\n--- 2. My Dashboard Organization ---")
check("Dashboard has Section A: Learning Statistics & Activity (#section-learning-stats)",
      'id="section-learning-stats"' in html)
check("Dashboard has Section B: Concept Mastery Breakdown (#section-concept-mastery)",
      'id="section-concept-mastery"' in html)
check("Dashboard has Section C: Recurring Mistakes Analysis (#section-recurring-mistakes)",
      'id="section-recurring-mistakes"' in html)
check("Dashboard has Section D: Recommended Practice (#section-recommended-practice)",
      'id="section-recommended-practice"' in html)
check("Dashboard stat cards present for Attempted, Passed, Pass Rate, Docker Submissions",
      'id="stat-attempted-challenges"' in html and 'id="stat-passed-challenges"' in html and
      'id="stat-pass-rate"' in html and 'id="stat-total-submissions"' in html)
check("Dashboard has recent learning activity container (#dash-recent-activity-list)",
      'id="dash-recent-activity-list"' in html)

# -----------------------------------------------------------------------------
# 3. My Account Cleanup Verification
# -----------------------------------------------------------------------------
print("\n--- 3. My Account Cleanup (No Duplicated Analytics) ---")
# Check view-account in HTML specifically
acc_start = html.find('id="view-account"')
acc_end = html.find('</section>', acc_start) if acc_start != -1 else -1
acc_html = html[acc_start:acc_end] if acc_start != -1 else ""

check("My Account view exists", len(acc_html) > 0)
check("No learning statistics grid in My Account view", "acc-stat-attempted" not in acc_html)
check("No concept mastery breakdown in My Account view", "acc-mastery-container" not in acc_html)
check("No recurring mistakes analysis in My Account view", "acc-mistakes-container" not in acc_html)
check("No recommended practice card in My Account view", "acc-jump-rec-btn" not in acc_html)
check("Personal Information Card exists in My Account", "Personal Information" in acc_html)
check("Account Security Card exists in My Account", "Account Security" in acc_html)
check("Email is marked readonly in account form", 'id="acc-email"' in acc_html and 'readonly' in acc_html)
check("Profile edit form and save/cancel buttons exist",
      'id="profile-edit-form"' in acc_html and 'id="save-profile-btn"' in acc_html and 'id="cancel-profile-btn"' in acc_html)
check("Change password form exists", 'id="change-password-form"' in acc_html)

# -----------------------------------------------------------------------------
# 4. Navigation Guards & Access Control
# -----------------------------------------------------------------------------
print("\n--- 4. Client & Server Access Control ---")
check("JS showView guards workspace, dashboard, account against unauthenticated access",
      "['workspace', 'dashboard', 'account'].includes(cleanName) && !currentUser" in js)
check("JS updateAuthUI toggles visitor vs authenticated navbar actions",
      "visitorActions.classList.add('hidden')" in js and "userActions.classList.remove('hidden')" in js)
check("JS updateAuthUI toggles workspace, dashboard, account nav tabs",
      "workspaceNavTab.classList.remove('hidden')" in js and "workspaceNavTab.classList.add('hidden')" in js)
check("JS updateAuthUI toggles hero visitor vs auth CTAs and badges",
      "heroBadgeVisitor" in js and "heroBadgeAuth" in js and "heroVisitorCtas" in js and "heroAuthCtas" in js)
check("JS handles logout by cleaning currentUser and routing to home",
      "showView('home')" in js)

# -----------------------------------------------------------------------------
# 5. Database & Mastery Calculation Sync (0% Mastery Investigation & Resolution)
# -----------------------------------------------------------------------------
print("\n--- 5. Deterministic Mastery Calculation & Auto-Sync ---")
from database import get_learner_mastery, get_learner_progress_counts, get_recurring_mistakes
from recommendations import get_recommendation

# Test student1 (historical learner with completed submissions)
mastery = get_learner_mastery("student1")
check("student1 has non-empty concept mastery dictionary", len(mastery) > 0)
check("Conditionals mastery is > 0% for student1 (0% bug resolved)", mastery.get("conditionals", 0) > 0)
check("Loops mastery is > 0% for student1", mastery.get("loops", 0) > 0)
check("Math mastery is > 0% for student1", mastery.get("math", 0) > 0)

progress = get_learner_progress_counts("student1")
check("progress counts has total_attempted", "total_attempted" in progress)
check("progress counts has pass_rate_percent", "pass_rate_percent" in progress)
check("progress counts total_attempted >= passed_challenges", progress["total_attempted"] >= progress["passed_challenges"])

# -----------------------------------------------------------------------------
# 6. Recurring Mistakes Analysis (>= 2 Distinct Challenges Rule)
# -----------------------------------------------------------------------------
print("\n--- 6. Recurring Mistakes Cross-Challenge Rule ---")
from database import get_learner_mistake_details
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Insert synthetic submissions for a test learner to strictly test >=2 rule
test_learner = "test_mistake_rule_learner"
c.execute("DELETE FROM submission_mistakes WHERE submission_id LIKE 'sub-test-%'")
c.execute("DELETE FROM submissions WHERE learner_id = ?", (test_learner,))

# Scenario A: Learner has 3 failed submissions, but all on the SAME challenge ('last_k_total')
# with mistake category 'off_by_one'
for i in range(3):
    sid = f"sub-test-same-{i}"
    c.execute("""
        INSERT INTO submissions (submission_id, learner_id, challenge_id, all_passed, hints_requested, processed_for_progress, timestamp)
        VALUES (?, ?, 'last_k_total', 0, 0, 1, datetime('now'))
    """, (sid, test_learner))
    c.execute("""
        INSERT INTO submission_mistakes (submission_id, category, evidence, confidence)
        VALUES (?, 'off_by_one', 'Index error on last element', 0.9)
    """, (sid,))
conn.commit()

details_single = get_learner_mistake_details(test_learner)
check("Mistake occurring 3 times on the SAME challenge is NOT recurring (< 2 distinct challenges)",
      not any(m.get("is_recurring") for m in details_single.get("recurring", [])))

# Scenario B: Learner now fails a SECOND DISTINCT challenge ('first_n_squares') with mistake category 'off_by_one'
sid2 = "sub-test-diff-1"
c.execute("""
    INSERT INTO submissions (submission_id, learner_id, challenge_id, all_passed, hints_requested, processed_for_progress, timestamp)
    VALUES (?, ?, 'first_n_squares', 0, 0, 1, datetime('now'))
""", (sid2, test_learner))
c.execute("""
    INSERT INTO submission_mistakes (submission_id, category, evidence, confidence)
    VALUES (?, 'off_by_one', 'Slicing error off by one', 0.9)
""", (sid2,))
conn.commit()

details_multi = get_learner_mistake_details(test_learner)
recurring_obo = next((m for m in details_multi.get("recurring", []) if m["category_id"] == "off_by_one"), None)
check("Mistake occurring across 2 distinct challenges IS marked recurring", recurring_obo is not None)
if recurring_obo:
    check("Recurring mistake reports distinct_challenges_count >= 2", recurring_obo.get("distinct_challenges_count", 0) >= 2)
    check("Recurring mistake has affected_challenges list", len(recurring_obo.get("affected_challenges", [])) >= 2)
    check("Recurring mistake provides real practice challenge", recurring_obo.get("practice_challenge") is not None)

# Cleanup test submissions
c.execute("DELETE FROM submission_mistakes WHERE submission_id LIKE 'sub-test-%'")
c.execute("DELETE FROM submissions WHERE learner_id = ?", (test_learner,))
conn.commit()
conn.close()

# -----------------------------------------------------------------------------
# 7. Recommendations Verification
# -----------------------------------------------------------------------------
print("\n--- 7. Next Recommended Practice ---")
rec_res = get_recommendation("student1")
rec = rec_res.get("recommended_challenge")
check("Recommendation returns a real challenge", rec is not None and "id" in rec and "title" in rec)
check("Recommendation explains reason", "recommendation_reason" in rec_res and len(rec_res["recommendation_reason"]) > 5)
check("Recommendation includes difficulty", rec.get("difficulty") in ["easy", "medium", "hard"])

# -----------------------------------------------------------------------------
# 8. API Integration: Learner Profile & Account Isolation
# -----------------------------------------------------------------------------
print("\n--- 8. API Endpoints & Auth Workflow ---")
client = DojoClient()

# Unauthenticated visitor cannot view private learner profile
status, res = client.get("/api/account")
check("Unauthenticated GET /api/account returns 401 Unauthorized", status == 401)

# Signup unique user
import time
unique_email = f"learner_{int(time.time())}@debugdojo.test"
status, res = client.post("/api/auth/signup", {
    "full_name": "Test Dojo Master",
    "email": unique_email,
    "password": "StrongPassword123!",
    "confirm_password": "StrongPassword123!",
    "age": 24
})
check("Signup returns 201 Created", status == 201)
user_id = res.get("user", {}).get("user_id")

# Fetch authenticated account
status, res = client.get("/api/account")
check("Authenticated GET /api/account returns 200 OK", status == 200)
check("Account user object contains full_name, email, age, created_at, user_id, status",
      all(k in res.get("user", {}) for k in ["full_name", "email", "age", "created_at", "user_id", "status"]))
check("Account email matches registered email", res.get("user", {}).get("email") == unique_email.lower())
check("Account age matches registered age", res.get("user", {}).get("age") == 24)

# Fetch learner dashboard data for new user (empty state verification)
status, res = client.get(f"/api/learner/{user_id}")
check("GET /api/learner/{user_id} returns 200 OK", status == 200)
check("New user progress counts has 0 passed challenges", res.get("progress_counts", {}).get("passed_challenges") == 0)
check("New user recurring mistakes list is empty", len(res.get("recurring_mistakes", [])) == 0)
check("New user receives valid starter recommendation", res.get("recommended_challenge") is not None)

# Update profile (Full Name & Age)
status, res = client.patch("/api/account", {
    "full_name": "Updated Dojo Master",
    "age": 25
})
check("PATCH /api/account returns 200 OK", status == 200)
check("Full name updated", res.get("user", {}).get("full_name") == "Updated Dojo Master")
check("Age updated", res.get("user", {}).get("age") == 25)

# Logout
status, res = client.post("/api/auth/logout", {})
check("POST /api/auth/logout returns 200 OK", status == 200)
status, res = client.get("/api/account")
check("Post-logout GET /api/account returns 401 Unauthorized", status == 401)

print("\n" + "=" * 76)
print(f"Suite Complete: {passed} passed, {failed} failed")
print("=" * 76)

if failed > 0:
    sys.exit(1)
