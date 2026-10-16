"""
test_phase5.py  —  Debug Dojo Phase 5 Comprehensive Test Suite
==============================================================
Validates:
  1. A mistake appearing in one challenge is NOT recurring.
  2. The same mistake across two distinct challenge IDs IS recurring.
  3. Multiple failures on the same challenge do NOT qualify as recurring.
  4. A pass without hints contributes more mastery than a pass after hints.
  5. Missing/new learners receive an appropriate new-learner response (HTTP 200).
  6. Invalid learner IDs (empty/whitespace) are rejected with HTTP 400.
  7. Recommendations target recorded recurring mistakes when suitable challenges exist.
  8. Recommendation reasons match actual learner data.
  9. Unknown challenge IDs are NEVER recommended.
 10. A submission cannot update mastery twice through repeated update requests (idempotency).
 11. Edge case: learner completing all challenges gets completion recommendation.
 12. Regressions check: Phase 1 (health), Phase 2 (catalogue), Phase 3 (submit), Phase 4 (hints & taxonomy) APIs still work.
"""

import sys
import os
import json
import uuid
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
    req = urllib.request.Request(url, method="GET")
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
    print("🥋 Debug Dojo Phase 5 Test Suite")
    print("=" * 70)

    # -----------------------------------------------------------------------
    # 1. Health check & Catalogue regression
    # -----------------------------------------------------------------------
    print("\n--- 1. Health check & Catalogue regression ---")
    st, d = get_json("/api/health")
    check("GET /api/health is 200 OK", st == 200 and d.get("status") == "ok")

    st, challenges = get_json("/api/challenges")
    check("GET /api/challenges returns 10 challenges", st == 200 and len(challenges) == 10)
    valid_cids = {ch["id"] for ch in challenges}

    # -----------------------------------------------------------------------
    # 2. New / Missing Learner Profile
    # -----------------------------------------------------------------------
    print("\n--- 2. Missing / New Learner Response ---")
    new_learner_id = f"new_student_{uuid.uuid4().hex[:6]}"
    st, profile = get_json(f"/api/learner/{new_learner_id}")
    check("New learner receives 200 OK", st == 200)
    check("Learner ID matches request", profile.get("learner_id") == new_learner_id)
    check("New learner has 0 recurring mistakes", profile.get("recurring_mistakes") == [])
    check("New learner has all concept masteries at 0", all(v == 0.0 for v in profile.get("mastery", {}).values()))
    check("Progress counts has 0 total submissions", profile.get("progress_counts", {}).get("total_submissions") == 0)
    check("Recommended challenge exists in catalogue", profile.get("next_recommended_challenge", {}).get("id") in valid_cids)
    check("Recommendation reason explains starting point", "Count Passes" in profile.get("explanation", "") or "welcome" in profile.get("explanation", "").lower())

    # -----------------------------------------------------------------------
    # 3. Invalid Learner ID Validation
    # -----------------------------------------------------------------------
    print("\n--- 3. Invalid Learner ID Validation ---")
    st, _ = get_json("/api/learner/%20")
    check("Whitespace learner ID returns 400", st == 400)

    too_long = "a" * 150
    st, _ = get_json(f"/api/learner/{too_long}")
    check("Excessively long learner ID returns 400", st == 400)

    # -----------------------------------------------------------------------
    # 4. Recurring Mistake Detection (One Challenge vs Two Challenges vs Repeated)
    # -----------------------------------------------------------------------
    print("\n--- 4. Mistake Taxonomy & Recurring Logic ---")
    # Learner A fails first_n_squares with off_by_one ONCE
    learner_a = f"learner_a_{uuid.uuid4().hex[:6]}"
    code_off_by_one_squares = """def first_n_squares(n):
    result = []
    for i in range(n):
        result.append(i * i)
    return result
"""
    st, sub1 = post_json("/api/submit", {
        "learner_id": learner_a,
        "challenge_id": "first_n_squares",
        "code": code_off_by_one_squares,
    })
    check("Submission 1 created", st == 200 and not sub1["all_passed"])
    check("Mistake tagged as off_by_one", any(m["category"] == "off_by_one" for m in sub1.get("mistakes", [])))

    st, prof_a1 = get_json(f"/api/learner/{learner_a}")
    check("Mistake in only ONE challenge is NOT recurring", "off_by_one" not in prof_a1.get("recurring_mistakes", []))

    # Learner A fails first_n_squares a SECOND time with same off_by_one bug
    st, sub2 = post_json("/api/submit", {
        "learner_id": learner_a,
        "challenge_id": "first_n_squares",
        "code": code_off_by_one_squares,
    })
    check("Submission 2 created", st == 200 and not sub2["all_passed"])

    st, prof_a2 = get_json(f"/api/learner/{learner_a}")
    check("Two failures on the SAME challenge do NOT qualify as recurring", "off_by_one" not in prof_a2.get("recurring_mistakes", []))
    check("Total submissions count is 2", prof_a2.get("progress_counts", {}).get("total_submissions") == 2)

    # Now Learner A fails a SECOND DISTINCT challenge (middle_three) with off_by_one
    code_off_by_one_mid = """def middle_three(items):
    if len(items) < 3:
        return items
    mid = len(items) // 2
    return items[mid - 1 : mid + 1]
"""
    st, sub3 = post_json("/api/submit", {
        "learner_id": learner_a,
        "challenge_id": "middle_three",
        "code": code_off_by_one_mid,
    })
    check("Submission 3 on second challenge created", st == 200 and not sub3["all_passed"])
    check("Mistake in second challenge tagged as off_by_one", any(m["category"] == "off_by_one" for m in sub3.get("mistakes", [])))

    st, prof_a3 = get_json(f"/api/learner/{learner_a}")
    check("Same mistake across TWO DISTINCT challenge IDs IS recurring", "off_by_one" in prof_a3.get("recurring_mistakes", []))

    # -----------------------------------------------------------------------
    # 5. Recommendation Targeting Recurring Mistake
    # -----------------------------------------------------------------------
    print("\n--- 5. Recommendation Targeting Recurring Mistakes ---")
    rec_ch = prof_a3.get("next_recommended_challenge")
    check("Recommendation returned", rec_ch is not None)
    check("Recommended challenge exists in catalogue", rec_ch.get("id") in valid_cids)
    check("Recommendation targets challenge addressing off_by_one", rec_ch.get("id") in ["first_n_squares", "middle_three", "last_k_total"])
    reason = prof_a3.get("explanation", "")
    check("Recommendation reason mentions recurring 'off_by_one' mistake", "off_by_one" in reason)
    check("Recommendation reason matches actual learner data", "recurring" in reason.lower())

    # -----------------------------------------------------------------------
    # 6. Concept Mastery: Pass without hints vs Pass with hints
    # -----------------------------------------------------------------------
    print("\n--- 6. Concept Mastery: Hints vs No-Hints ---")
    learner_clean = f"learner_clean_{uuid.uuid4().hex[:6]}"
    learner_hinted = f"learner_hinted_{uuid.uuid4().hex[:6]}"

    perfect_code_rev = """def reverse_string(text):
    result = ""
    for ch in text:
        result = ch + result
    return result
"""

    # Learner Clean passes reverse_string with 0 hints
    st, res_clean = post_json("/api/submit", {
        "learner_id": learner_clean,
        "challenge_id": "reverse_string",
        "code": perfect_code_rev,
    })
    check("Learner Clean submission passed", st == 200 and res_clean.get("all_passed"))

    # Learner Hinted requests hints first, then passes
    broken_code_rev = """def reverse_string(text):
    result = ""
    for ch in text:
        result = result + ch
    return result
"""
    st, res_broken = post_json("/api/submit", {
        "learner_id": learner_hinted,
        "challenge_id": "reverse_string",
        "code": broken_code_rev,
    })
    sub_id_broken = res_broken["submission_id"]
    # Request a hint
    st, hint_res = post_json("/api/hint", {"submission_id": sub_id_broken})
    check("Hint requested for learner hinted", st == 200 and hint_res.get("status") == "active")

    # Learner Hinted now submits passing code
    st, res_hinted_pass = post_json("/api/submit", {
        "learner_id": learner_hinted,
        "challenge_id": "reverse_string",
        "code": perfect_code_rev,
    })
    check("Learner Hinted submission passed", st == 200 and res_hinted_pass.get("all_passed"))

    # Compare masteries on 'strings' concept (reverse_string is tagged: ['strings', 'iteration'])
    st, prof_clean = get_json(f"/api/learner/{learner_clean}")
    st, prof_hinted = get_json(f"/api/learner/{learner_hinted}")

    mastery_clean_strings = prof_clean.get("mastery", {}).get("strings", 0.0)
    mastery_hinted_strings = prof_hinted.get("mastery", {}).get("strings", 0.0)

    check(
        "Pass without hints contributes MORE mastery than pass after hints",
        mastery_clean_strings > mastery_hinted_strings,
        f"Clean: {mastery_clean_strings}%, Hinted: {mastery_hinted_strings}%"
    )
    check("Clean pass gave 25 points", mastery_clean_strings == 25.0)

    # -----------------------------------------------------------------------
    # 7. Idempotency: Repeated update cannot update mastery twice
    # -----------------------------------------------------------------------
    print("\n--- 7. Idempotent Progress Updates ---")
    clean_sub_id = res_clean["submission_id"]

    # Try updating progress again with the same clean submission ID
    st, update1 = post_json("/api/learner/update_progress", {"submission_id": clean_sub_id})
    check("Update progress endpoint responds 200", st == 200)
    check("Submission already processed, applied is False", update1.get("applied") is False)

    st, prof_clean_after = get_json(f"/api/learner/{learner_clean}")
    mastery_after = prof_clean_after.get("mastery", {}).get("strings", 0.0)
    check(
        "Repeated update request did NOT increase mastery twice",
        mastery_after == mastery_clean_strings,
        f"Initial: {mastery_clean_strings}%, After second update: {mastery_after}%"
    )

    # -----------------------------------------------------------------------
    # 8. Recommendation: Prioritizing lowest concept mastery & avoiding mastered
    # -----------------------------------------------------------------------
    print("\n--- 8. Recommendation: Avoiding Mastered & Lowest Mastery ---")
    rec_clean = prof_clean.get("next_recommended_challenge")
    check("Recommended challenge is NOT the already-passed 'reverse_string'", rec_clean.get("id") != "reverse_string")
    check("Recommendation reason explains skill building", "mastery" in prof_clean.get("explanation", "").lower() or "recommend" in prof_clean.get("explanation", "").lower())

    # -----------------------------------------------------------------------
    # 9. Never Recommend Unknown Challenge IDs
    # -----------------------------------------------------------------------
    print("\n--- 9. Unknown Challenge IDs Are Never Recommended ---")
    for l_id in [new_learner_id, learner_a, learner_clean, learner_hinted]:
        _, p = get_json(f"/api/learner/{l_id}")
        rec = p.get("next_recommended_challenge")
        if rec:
            check(f"Recommendation for {l_id[:12]} is a valid catalogue challenge", rec.get("id") in valid_cids)

    # -----------------------------------------------------------------------
    # 10. Completion Edge Case: All challenges completed
    # -----------------------------------------------------------------------
    print("\n--- 10. Completion Edge Case ---")
    from challenges import CHALLENGES
    learner_completer = f"learner_comp_{uuid.uuid4().hex[:6]}"
    from database import get_connection

    # Simulate completion of all challenges directly in database
    with get_connection() as conn:
        for ch in CHALLENGES:
            cid = ch["id"]
            sub_id = f"sub_comp_{uuid.uuid4().hex[:8]}"
            conn.execute("""
                INSERT INTO submissions (
                    submission_id, learner_id, challenge_id, all_passed,
                    hints_requested, timestamp, processed_for_progress
                ) VALUES (?, ?, ?, 1, 0, '2026-10-16T12:00:00Z', 1)
            """, (sub_id, learner_completer, cid))
        conn.commit()

    st, prof_comp = get_json(f"/api/learner/{learner_completer}")
    check("Learner who completed all challenges has 10 passed challenges", prof_comp.get("progress_counts", {}).get("passed_challenges") == 10)
    check("Next recommended challenge is None when all completed", prof_comp.get("next_recommended_challenge") is None)
    check("Explanation congratulates learner on completing all challenges", "congratulations" in prof_comp.get("explanation", "").lower() or "completed" in prof_comp.get("explanation", "").lower())

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    print("\n" + "=" * 70)
    print(f"Results: {PASS} passed, {FAIL} failed")
    print("=" * 70)
    if FAIL > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
