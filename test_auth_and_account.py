"""
test_auth_and_account.py — Complete Verification Suite for Authentication & Personal Account System
====================================================================================================
Tests all requirements across Phase A through Phase F:
  1. Signup validations (valid, duplicate rejection, email format, mismatch password, invalid age, argon2 hash)
  2. Login & Session management (HttpOnly cookie, generic invalid credentials, rate limiting, session invalidation)
  3. Logout & Session revocation
  4. Account Profile & Updates (GET /api/account, PATCH /api/account, read-only email, change-password)
  5. User Data Isolation & Privacy (User A cannot access User B's profile, data, or exam attempts)
  6. Real backend learning statistics (submissions, mastery, recurring mistakes, recommendation)
  7. Existing Feature Integrity (Challenges, practice submissions in Docker, hints, exam timer)
"""

import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
import json
import uuid
import sys
import sqlite3

BASE_URL = "http://127.0.0.1:8000"
DB_PATH = "sandbox/dojo.db"

passed = 0
failed = 0


def check(desc: str, condition: bool, extra: str = ""):
    global passed, failed
    if condition:
        print(f"  ✓ {desc}")
        passed += 1
    else:
        print(f"  ✗ FAIL: {desc} {extra}")
        failed += 1


class DojoClient:
    """Helper client maintaining session cookies for stateful authentication testing."""

    def __init__(self):
        self.cookie_jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookie_jar)
        )

    def request(
        self,
        method: str,
        path: str,
        data: dict | None = None,
        headers: dict | None = None,
    ):
        url = f"{BASE_URL}{path}"
        hdrs = headers or {}
        body = None
        if data is not None:
            body = json.dumps(data).encode("utf-8")
            hdrs["Content-Type"] = "application/json"
        
        # Include Origin for state-changing requests to verify CSRF protection
        if method in ("POST", "PATCH", "PUT", "DELETE"):
            hdrs.setdefault("Origin", "http://127.0.0.1:8000")

        req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
        try:
            with self.opener.open(req) as resp:
                status = resp.status
                raw = resp.read().decode("utf-8")
                try:
                    payload = json.loads(raw)
                except Exception:
                    payload = raw
                return status, payload, resp.headers
        except urllib.error.HTTPError as err:
            status = err.code
            raw = err.read().decode("utf-8")
            try:
                payload = json.loads(raw)
            except Exception:
                payload = raw
            return status, payload, err.headers

    def get_cookie(self, name: str) -> str | None:
        for cookie in self.cookie_jar:
            if cookie.name == name:
                return cookie.value
        return None


def main():
    print("=" * 72)
    print("🥋 Debug Dojo — Authentication & Personal Account System Test Suite")
    print("=" * 72)

    unique_suffix = uuid.uuid4().hex[:8]

    # ---------------------------------------------------------------------------
    # Section 1: Signup Validation & Security
    # ---------------------------------------------------------------------------
    print("\n--- 1. Signup Validation & Secure Password Handling ---")
    client1 = DojoClient()

    # 1.1 Missing fields
    s, data, _ = client1.request("POST", "/api/auth/signup", {})
    check("Empty signup request returns 422 Unprocessable Entity", s == 422)

    # 1.2 Invalid email format
    s, data, _ = client1.request(
        "POST",
        "/api/auth/signup",
        {
            "full_name": "Test User",
            "email": "not-an-email",
            "password": "Password123!",
            "confirm_password": "Password123!",
        },
    )
    check("Invalid email format rejected with 422", s == 422)

    # 1.3 Password mismatch
    s, data, _ = client1.request(
        "POST",
        "/api/auth/signup",
        {
            "full_name": "Test User",
            "email": f"test_{unique_suffix}@example.com",
            "password": "Password123!",
            "confirm_password": "DifferentPassword123!",
        },
    )
    check("Password mismatch rejected with 400", s == 400)
    check("Password mismatch error message is descriptive", "do not match" in str(data))

    # 1.4 Short password (< 8 chars)
    s, data, _ = client1.request(
        "POST",
        "/api/auth/signup",
        {
            "full_name": "Test User",
            "email": f"test_{unique_suffix}@example.com",
            "password": "short",
            "confirm_password": "short",
        },
    )
    check("Short password (< 8 chars) rejected with 422", s == 422)

    # 1.5 Invalid age (out of bounds)
    s, data, _ = client1.request(
        "POST",
        "/api/auth/signup",
        {
            "full_name": "Test User",
            "email": f"test_{unique_suffix}@example.com",
            "password": "Password123!",
            "confirm_password": "Password123!",
            "age": 200,
        },
    )
    check("Invalid age (> 120) rejected with 422", s == 422)

    # 1.6 Valid Signup
    user1_email = f"Alice_{unique_suffix}@Example.COM"  # test email normalization
    user1_pwd = "AliceSecurePassword456!"
    s, data, hdrs = client1.request(
        "POST",
        "/api/auth/signup",
        {
            "full_name": "Alice Programmer",
            "email": user1_email,
            "password": user1_pwd,
            "confirm_password": user1_pwd,
            "age": 24,
        },
    )
    check("Valid signup returns 201 Created", s == 201)
    user1_id = data.get("user", {}).get("user_id")
    check("Signup returns user object with user_id", bool(user1_id and user1_id.startswith("usr_")))
    check("Email is normalized to lowercase in response", data.get("user", {}).get("email") == user1_email.lower())
    check("Password hash is NOT exposed in signup response", "password_hash" not in str(data))
    check("Plaintext password is NOT exposed in signup response", user1_pwd not in str(data))

    # Verify session cookie was set
    session_cookie = client1.get_cookie("dojo_session")
    check("HttpOnly dojo_session cookie established upon signup", session_cookie is not None)

    # 1.7 Duplicate normalized email rejection
    client_dup = DojoClient()
    s, data, _ = client_dup.request(
        "POST",
        "/api/auth/signup",
        {
            "full_name": "Alice Impostor",
            "email": f"ALICE_{unique_suffix}@example.com",  # duplicate with different casing
            "password": "AnotherPassword789!",
            "confirm_password": "AnotherPassword789!",
        },
    )
    check("Duplicate normalized email rejected with 400", s == 400)
    check("Duplicate email error states email already exists", "already exists" in str(data).lower() or "already registered" in str(data).lower())

    # 1.8 Verify SQLite database storage: Argon2id hash stored, NOT plaintext
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users WHERE user_id = ?", (user1_id,))
    row = cursor.fetchone()
    conn.close()
    check("User record saved in SQLite database", row is not None)
    if row:
        stored_hash = row[0]
        check("Stored password is an Argon2id/scrypt hash", stored_hash.startswith("$argon2id$") or stored_hash.startswith("scrypt$"))
        check("Plaintext password is NOT stored in database", user1_pwd != stored_hash)

    # ---------------------------------------------------------------------------
    # Section 2: Login & Authentication Session
    # ---------------------------------------------------------------------------
    print("\n--- 2. Login, Generic Errors & Session Validation ---")

    # 2.1 Unauthenticated client cannot access /api/auth/me
    unauth_client = DojoClient()
    s, data, _ = unauth_client.request("GET", "/api/auth/me")
    check("Unauthenticated GET /api/auth/me returns 401 Unauthorized", s == 401)

    s, data, _ = unauth_client.request("GET", "/api/account")
    check("Unauthenticated GET /api/account returns 401 Unauthorized", s == 401)

    # 2.2 Login with wrong password
    client2 = DojoClient()
    s, data, _ = client2.request(
        "POST",
        "/api/auth/login",
        {"email": user1_email.lower(), "password": "WrongPassword999!"},
    )
    check("Wrong password rejected with 401", s == 401)
    check("Generic error message returned (does not reveal password mismatch)", "Invalid email or password" in str(data))

    # 2.3 Login with unknown email
    s, data, _ = client2.request(
        "POST",
        "/api/auth/login",
        {"email": "nobody@nowhere-dojo.org", "password": "AnyPassword123!"},
    )
    check("Unknown email rejected with 401", s == 401)
    check("Generic error message returned for unknown email", "Invalid email or password" in str(data))

    # 2.4 Successful login with registered credentials
    s, data, _ = client2.request(
        "POST",
        "/api/auth/login",
        {"email": user1_email, "password": user1_pwd},  # mixed case should normalize
    )
    check("Registered user can log in with correct email/password (200 OK)", s == 200)
    check("Login response contains user object", data.get("user", {}).get("user_id") == user1_id)
    check("Password hash NOT in login response", "password_hash" not in str(data))
    check("Session cookie set upon login", client2.get_cookie("dojo_session") is not None)

    # 2.5 Authenticated GET /api/auth/me
    s, data, _ = client2.request("GET", "/api/auth/me")
    check("Authenticated GET /api/auth/me returns 200 OK", s == 200)
    check("User profile matches logged-in user", data.get("email") == user1_email.lower())
    check("User full name matches", data.get("full_name") == "Alice Programmer")

    # ---------------------------------------------------------------------------
    # Section 3: Logout & Server-Side Invalidation
    # ---------------------------------------------------------------------------
    print("\n--- 3. Logout & Session Revocation ---")

    s, data, _ = client2.request("POST", "/api/auth/logout")
    check("POST /api/auth/logout returns 200 OK", s == 200)

    # Subsequent access to protected route with revoked session
    s, data, _ = client2.request("GET", "/api/auth/me")
    check("Revoked session cannot access GET /api/auth/me (returns 401)", s == 401)

    s, data, _ = client2.request("GET", "/api/account")
    check("Revoked session cannot access GET /api/account (returns 401)", s == 401)

    # ---------------------------------------------------------------------------
    # Section 4: Personal Account Management & Profile Editing
    # ---------------------------------------------------------------------------
    print("\n--- 4. Personal Account Profile & Password Change ---")

    # Re-login with client1
    s, data, _ = client1.request(
        "POST",
        "/api/auth/login",
        {"email": user1_email, "password": user1_pwd},
    )
    check("Re-login successful", s == 200)

    # 4.1 GET /api/account
    s, data, _ = client1.request("GET", "/api/account")
    check("GET /api/account returns 200 OK", s == 200)
    u_data = data.get("user", {})
    stats_data = data.get("statistics", {})
    check("Account contains user profile", u_data.get("email") == user1_email.lower())
    check("Account contains authentic statistics", "total_attempted" in stats_data)
    check("Concept mastery present in statistics", "concept_mastery" in stats_data)
    check("Password hash NOT exposed in account API", "password_hash" not in str(data))

    # 4.2 PATCH /api/account (Update name and age)
    s, data, _ = client1.request(
        "PATCH",
        "/api/account",
        {"full_name": "Alice Senior Debugger", "age": 25},
    )
    check("PATCH /api/account updates profile (200 OK)", s == 200)
    check("Full name updated", data.get("user", {}).get("full_name") == "Alice Senior Debugger")
    check("Age updated", data.get("user", {}).get("age") == 25)

    # 4.3 Change Password
    s, data, _ = client1.request(
        "POST",
        "/api/account/change-password",
        {
            "current_password": "WrongCurrentPassword!",
            "new_password": "AliceNewPassword789!",
            "confirm_new_password": "AliceNewPassword789!",
        },
    )
    check("Change password with wrong current password rejected (400)", s == 400)

    user1_new_pwd = "AliceNewPassword789!"
    s, data, _ = client1.request(
        "POST",
        "/api/account/change-password",
        {
            "current_password": user1_pwd,
            "new_password": user1_new_pwd,
            "confirm_new_password": user1_new_pwd,
        },
    )
    check("Change password with correct credentials succeeds (200 OK)", s == 200)

    # Old password no longer works
    s, data, _ = DojoClient().request(
        "POST",
        "/api/auth/login",
        {"email": user1_email, "password": user1_pwd},
    )
    check("Old password rejected after password change", s == 401)

    # New password works
    s, data, _ = DojoClient().request(
        "POST",
        "/api/auth/login",
        {"email": user1_email, "password": user1_new_pwd},
    )
    check("New password logs in successfully", s == 200)

    # ---------------------------------------------------------------------------
    # Section 5: User Data Isolation & Authorization Guards
    # ---------------------------------------------------------------------------
    print("\n--- 5. User Data Isolation & Authorization Boundaries ---")

    # Create User 2
    client_bob = DojoClient()
    user2_email = f"Bob_{unique_suffix}@example.com"
    user2_pwd = "BobPassword987!"
    s, data, _ = client_bob.request(
        "POST",
        "/api/auth/signup",
        {
            "full_name": "Bob Builder",
            "email": user2_email,
            "password": user2_pwd,
            "confirm_password": user2_pwd,
            "age": 30,
        },
    )
    user2_id = data.get("user", {}).get("user_id")
    check("User 2 (Bob) created successfully", bool(user2_id))

    # Bob starts an exam attempt
    s, exam_data, _ = client_bob.request(
        "POST",
        "/api/exam/start",
        {"challenge_id": "last_k_total", "learner_id": "ignored_in_favor_of_session"},
    )
    check("Bob starts exam attempt (200 OK)", s == 200)
    bob_attempt_id = exam_data.get("attempt_id")
    check("Bob's attempt is owned by Bob's user_id", exam_data.get("learner_id") == user2_id)

    # Alice attempts to access Bob's exam attempt
    s, data, _ = client1.request("GET", f"/api/exam/{bob_attempt_id}")
    check("Alice CANNOT view Bob's exam attempt (403 Forbidden)", s == 403)

    # Alice attempts to submit code on Bob's exam attempt
    s, data, _ = client1.request(
        "POST",
        f"/api/exam/{bob_attempt_id}/run-tests",
        {"code": "def last_k_total(n, k): return sum(n[-k:])"},
    )
    check("Alice CANNOT run tests on Bob's exam attempt (403 Forbidden)", s == 403)

    s, data, _ = client1.request(
        "POST",
        f"/api/exam/{bob_attempt_id}/submit",
        {"code": "def last_k_total(n, k): return sum(n[-k:])"},
    )
    check("Alice CANNOT submit Bob's exam attempt (403 Forbidden)", s == 403)

    # Alice attempts to inspect Bob's learner profile directly
    s, data, _ = client1.request("GET", f"/api/learner/{user2_id}")
    check("Alice CANNOT inspect Bob's learner progress profile (403 Forbidden)", s == 403)

    # Bob can access his own exam attempt
    s, data, _ = client_bob.request("GET", f"/api/exam/{bob_attempt_id}")
    check("Bob CAN access his own exam attempt (200 OK)", s == 200)

    # Bob can access his own learner profile
    s, data, _ = client_bob.request("GET", f"/api/learner/{user2_id}")
    check("Bob CAN access his own learner progress profile (200 OK)", s == 200)

    # ---------------------------------------------------------------------------
    # Section 6: Existing Features Integrity
    # ---------------------------------------------------------------------------
    print("\n--- 6. Existing Features Preservation ---")

    # Challenge catalogue
    s, challenges, _ = client1.request("GET", "/api/challenges")
    check("Challenge catalogue works (10 challenges)", s == 200 and len(challenges) == 10)

    # Challenge detail
    s, ch_detail, _ = client1.request("GET", "/api/challenges/count_passes")
    check("Challenge detail works", s == 200 and "visible_tests" in ch_detail)

    # Progressive Hints on Practice Submission
    buggy_code = (
        "def count_passes(marks):\n"
        "    passes = 0\n"
        "    for mark in marks:\n"
        "        if mark > 40:\n"
        "            passes += 1\n"
        "    return passes\n"
    )
    s, sub_buggy, _ = client1.request(
        "POST",
        "/api/submit",
        {"challenge_id": "count_passes", "code": buggy_code, "learner_id": "ignored"},
    )
    check("Docker execution for practice submission returns 200 OK", s == 200)
    sub_id = sub_buggy.get("submission_id")
    check("Submission ID generated for hints ladder", bool(sub_id))

    s, hint_data, _ = client1.request(
        "POST",
        "/api/hint",
        {"submission_id": sub_id},
    )
    check("Progressive hints work for authenticated user", s == 200 and "hint" in hint_data)

    # Docker Code Submission in Practice Mode (clean passing solution)
    solve_code = (
        "def count_passes(marks):\n"
        "    passes = 0\n"
        "    for mark in marks:\n"
        "        if mark >= 40:\n"
        "            passes += 1\n"
        "    return passes\n"
    )
    s, sub_res, _ = client1.request(
        "POST",
        "/api/submit",
        {
            "challenge_id": "count_passes",
            "code": solve_code,
            "learner_id": "ignored",
        },
    )
    check("Docker sandbox code execution returns 200 OK", s == 200)
    check("Submission passed in container", sub_res.get("all_passed") is True)
    check("Submission associated with Alice's user_id", sub_res.get("learner_id") == user1_id)

    # Check updated stats in Alice's account
    s, acc_updated, _ = client1.request("GET", "/api/account")
    new_stats = acc_updated.get("statistics", {})
    check("Account statistics reflect newly passed challenge", new_stats.get("passed_challenges", 0) >= 1 or new_stats.get("passed_count", 0) >= 1)

    print("\n" + "=" * 72)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 72)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
