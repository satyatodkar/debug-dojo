import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase_client: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"[Supabase] Init error: {e}")

"""
database.py  —  Debug Dojo Phase 5
==================================
SQLite-backed persistent storage for learner progress, concept mastery,
submissions, mistake categories, and hints.

Key principles:
  • Pseudonymous learner IDs only – no passwords or personal info stored.
  • Idempotency: progress updates for a submission apply AT MOST ONCE.
  • Safe table migrations via CREATE TABLE IF NOT EXISTS.
  • Deterministic concept mastery scoring formula (0–100).
"""

import sqlite3
import json
import secrets
import hashlib
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Any

try:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError, InvalidHash
    _ph = PasswordHasher()
except Exception:
    _ph = None

from challenges import CHALLENGES, CHALLENGE_BY_ID

DB_PATH = Path(__file__).parent / "sandbox" / "dojo.db"

# All distinct concepts from the catalogue
ALL_CONCEPTS = sorted(list({
    tag
    for ch in CHALLENGES
    for tag in ch.get("tags", [])
}))

# The five required mistake categories
REQUIRED_MISTAKE_CATEGORIES = {
    "off_by_one",
    "unhandled_short_input",
    "print_not_return",
    "boundary_comparison",
    "mutates_input",
}

# ---------------------------------------------------------------------------
# Mastery Formula Parameters
# ---------------------------------------------------------------------------
# Starting score for any concept is 0.0.
# On a pass without hints: +25.0 points per concept tagged to the challenge.
# On a pass after hints:   +15.0 points per concept tagged to the challenge.
# On a failure:            -5.0 points (floored at 0.0).
# Final mastery is clamped to [0.0, 100.0].
POINTS_PASS_NO_HINTS = 25.0
POINTS_PASS_WITH_HINTS = 15.0
POINTS_FAIL_PENALTY = -5.0


def get_connection() -> sqlite3.Connection:
    """Open SQLite connection with row_factory configured."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    """
    Initialize SQLite database tables and indexes safely.
    Preserves all existing data.
    """
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS submissions (
                submission_id TEXT PRIMARY KEY,
                learner_id TEXT NOT NULL,
                challenge_id TEXT NOT NULL,
                all_passed INTEGER NOT NULL,
                hints_requested INTEGER NOT NULL DEFAULT 0,
                timestamp TEXT NOT NULL,
                code TEXT,
                summary TEXT,
                processed_for_progress INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS submission_mistakes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                submission_id TEXT NOT NULL,
                category TEXT NOT NULL,
                evidence TEXT,
                confidence TEXT,
                FOREIGN KEY (submission_id) REFERENCES submissions(submission_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS submission_concepts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                submission_id TEXT NOT NULL,
                concept TEXT NOT NULL,
                FOREIGN KEY (submission_id) REFERENCES submissions(submission_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS learner_concept_mastery (
                learner_id TEXT NOT NULL,
                concept TEXT NOT NULL,
                mastery REAL NOT NULL DEFAULT 0.0,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (learner_id, concept)
            );

            CREATE TABLE IF NOT EXISTS exam_attempts (
                attempt_id TEXT PRIMARY KEY,
                learner_id TEXT NOT NULL,
                challenge_id TEXT NOT NULL,
                start_time TEXT NOT NULL,
                deadline TEXT NOT NULL,
                duration_seconds INTEGER NOT NULL,
                status TEXT NOT NULL,
                submitted_code TEXT,
                submitted_at TEXT,
                final_results TEXT,
                all_passed INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS exam_integrity_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attempt_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                details TEXT,
                FOREIGN KEY (attempt_id) REFERENCES exam_attempts(attempt_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS exam_hints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attempt_id TEXT NOT NULL,
                learner_id TEXT NOT NULL,
                challenge_id TEXT NOT NULL,
                hint_index INTEGER NOT NULL,
                stage TEXT NOT NULL,
                hint_text TEXT NOT NULL,
                requested_at TEXT NOT NULL,
                submission_id TEXT,
                FOREIGN KEY (attempt_id) REFERENCES exam_attempts(attempt_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                age INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active'
            );

            CREATE TABLE IF NOT EXISTS user_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                is_revoked INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_submissions_learner ON submissions(learner_id);
            CREATE INDEX IF NOT EXISTS idx_submissions_challenge ON submissions(challenge_id);
            CREATE INDEX IF NOT EXISTS idx_mistakes_sub ON submission_mistakes(submission_id);
            CREATE INDEX IF NOT EXISTS idx_mistakes_cat ON submission_mistakes(category);
            CREATE INDEX IF NOT EXISTS idx_exam_attempts_learner ON exam_attempts(learner_id);
            CREATE INDEX IF NOT EXISTS idx_exam_attempts_challenge ON exam_attempts(challenge_id);
            CREATE INDEX IF NOT EXISTS idx_exam_integrity_attempt ON exam_integrity_events(attempt_id);
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
            CREATE INDEX IF NOT EXISTS idx_sessions_user ON user_sessions(user_id);
            CREATE INDEX IF NOT EXISTS idx_sessions_expires ON user_sessions(expires_at);
        """)
        conn.commit()

    _migrate_from_json_if_needed()


def _migrate_from_json_if_needed() -> None:
    """
    Import existing Phase 4 submissions from sandbox/.submissions.json
    into SQLite if not already present, preserving prior hackathon data.
    """
    json_path = DB_PATH.parent / ".submissions.json"
    if not json_path.exists():
        return

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            old_data = json.load(f)
    except Exception:
        return

    if not isinstance(old_data, dict):
        return

    with get_connection() as conn:
        for sub_id, item in old_data.items():
            if not isinstance(item, dict):
                continue

            # Check if already in DB
            cur = conn.execute("SELECT submission_id FROM submissions WHERE submission_id = ?", (sub_id,))
            if cur.fetchone():
                continue

            learner_id = item.get("learner_id", "student1")
            challenge_id = item.get("challenge_id", "")
            all_passed = 1 if item.get("all_passed") else 0
            hints_req = item.get("hint_index", 0)
            timestamp = datetime.now(timezone.utc).isoformat()
            code = item.get("code", "")
            summary = item.get("summary", "")

            conn.execute("""
                INSERT INTO submissions (
                    submission_id, learner_id, challenge_id, all_passed,
                    hints_requested, timestamp, code, summary, processed_for_progress
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (sub_id, learner_id, challenge_id, all_passed, hints_req, timestamp, code, summary))

            # Migrate mistakes
            for m in item.get("mistakes", []):
                cat = m.get("category")
                if cat in REQUIRED_MISTAKE_CATEGORIES:
                    conn.execute("""
                        INSERT INTO submission_mistakes (submission_id, category, evidence, confidence)
                        VALUES (?, ?, ?, ?)
                    """, (sub_id, cat, m.get("evidence", ""), m.get("confidence", "medium")))

            # Migrate concepts
            ch_meta = CHALLENGE_BY_ID.get(challenge_id.replace("-", "_"))
            if ch_meta:
                for tag in ch_meta.get("tags", []):
                    conn.execute("""
                        INSERT INTO submission_concepts (submission_id, concept)
                        VALUES (?, ?)
                    """, (sub_id, tag))

        conn.commit()


# ---------------------------------------------------------------------------
# Submission & Hint Recording
# ---------------------------------------------------------------------------

def record_submission(sub_data: dict[str, Any]) -> None:
    """
    Persist a submission and its associated mistake categories and concept tags.
    """
    sub_id = sub_data["submission_id"]
    learner_id = sub_data["learner_id"]
    challenge_id = sub_data["challenge_id"]
    all_passed = 1 if sub_data.get("all_passed") else 0
    hints_req = sub_data.get("hint_index", 0)
    timestamp = datetime.now(timezone.utc).isoformat()
    code = sub_data.get("code", "")
    summary = sub_data.get("summary", "")

    cid_clean = challenge_id.replace("-", "_")
    ch_meta = CHALLENGE_BY_ID.get(cid_clean, {})
    tags = ch_meta.get("tags", [])

    with get_connection() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO submissions (
                submission_id, learner_id, challenge_id, all_passed,
                hints_requested, timestamp, code, summary, processed_for_progress
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
        """, (sub_id, learner_id, challenge_id, all_passed, hints_req, timestamp, code, summary))

        # Clear any prior recorded mistakes for this sub_id before re-inserting
        conn.execute("DELETE FROM submission_mistakes WHERE submission_id = ?", (sub_id,))
        for m in sub_data.get("mistakes", []):
            cat = m.get("category")
            if cat in REQUIRED_MISTAKE_CATEGORIES:
                conn.execute("""
                    INSERT INTO submission_mistakes (submission_id, category, evidence, confidence)
                    VALUES (?, ?, ?, ?)
                """, (sub_id, cat, m.get("evidence", ""), m.get("confidence", "medium")))

        # Record concepts
        conn.execute("DELETE FROM submission_concepts WHERE submission_id = ?", (sub_id,))
        for tag in tags:
            conn.execute("""
                INSERT INTO submission_concepts (submission_id, concept)
                VALUES (?, ?)
            """, (sub_id, tag))

        conn.commit()


    # Sync to Supabase
    if supabase_client:
        try:
            supabase_client.table("submissions").insert({
                "learner_id": learner_id,
                "challenge_id": str(challenge_id),
                "code": code,
                "status": "passed" if all_passed else "failed",
                "tests_passed": 1 if all_passed else 0,
                "tests_total": 1,
                "error_message": summary if not all_passed else None
            }).execute()
        except Exception as sb_err:
            print(f"[Supabase] Sync error: {sb_err}")


def increment_submission_hint(submission_id: str) -> int:
    """
    Increment hint counter for a submission in SQLite.
    Returns the new hint count.
    """
    with get_connection() as conn:
        conn.execute("""
            UPDATE submissions
            SET hints_requested = hints_requested + 1
            WHERE submission_id = ?
        """, (submission_id,))
        conn.commit()

        cur = conn.execute("SELECT hints_requested FROM submissions WHERE submission_id = ?", (submission_id,))
        row = cur.fetchone()
        return row["hints_requested"] if row else 1


# ---------------------------------------------------------------------------
# Concept Mastery & Progress (Idempotent)
# ---------------------------------------------------------------------------

def process_submission_progress(submission_id: str) -> bool:
    """
    Apply concept mastery updates for a submission.

    IDEMPOTENCY GUARANTEE:
    Checks `processed_for_progress`. If already 1, does nothing and returns False.
    Otherwise updates mastery, marks processed_for_progress = 1, and returns True.
    """
    with get_connection() as conn:
        cur = conn.execute("""
            SELECT submission_id, learner_id, challenge_id, all_passed,
                   hints_requested, processed_for_progress
            FROM submissions
            WHERE submission_id = ?
        """, (submission_id,))
        sub = cur.fetchone()

        if not sub:
            return False

        # If already processed, ensure progress is updated at most once!
        if sub["processed_for_progress"] == 1:
            return False

        learner_id = sub["learner_id"]
        challenge_id = sub["challenge_id"].replace("-", "_")
        all_passed = bool(sub["all_passed"])
        hints_req = sub["hints_requested"]

        # Check if the learner previously requested hints on this challenge
        cur_prior_hints = conn.execute("""
            SELECT SUM(hints_requested) as total_hints
            FROM submissions
            WHERE learner_id = ? AND challenge_id = ?
        """, (learner_id, sub["challenge_id"]))
        row_prior = cur_prior_hints.fetchone()
        prior_hints = (row_prior["total_hints"] or 0) if row_prior else 0

        hints_used_for_challenge = max(hints_req, prior_hints)

        # Retrieve challenge concepts
        ch_meta = CHALLENGE_BY_ID.get(challenge_id)
        tags = ch_meta.get("tags", []) if ch_meta else []

        # Mastery delta calculation
        if all_passed:
            if hints_used_for_challenge == 0:
                delta = POINTS_PASS_NO_HINTS       # +25.0
            else:
                delta = POINTS_PASS_WITH_HINTS     # +15.0
        else:
            delta = 0.0                            # Failed attempts receive no pass reward (0%)

        now_str = datetime.now(timezone.utc).isoformat()

        # Update mastery for each associated concept
        for concept in tags:
            cur_m = conn.execute("""
                SELECT mastery FROM learner_concept_mastery
                WHERE learner_id = ? AND concept = ?
            """, (learner_id, concept))
            row_m = cur_m.fetchone()
            current_val = row_m["mastery"] if row_m else 0.0

            # Compute new clamped value [0.0, 100.0]
            new_val = max(0.0, min(100.0, current_val + delta))

            conn.execute("""
                INSERT INTO learner_concept_mastery (learner_id, concept, mastery, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(learner_id, concept) DO UPDATE SET
                    mastery = excluded.mastery,
                    updated_at = excluded.updated_at
            """, (learner_id, concept, round(new_val, 1), now_str))

        # Mark submission as processed
        conn.execute("""
            UPDATE submissions
            SET processed_for_progress = 1
            WHERE submission_id = ?
        """, (submission_id,))

        conn.commit()
        return True


def sync_learner_unprocessed_submissions(learner_id: str) -> None:
    """
    Ensure all recorded submissions for the learner have been processed for progress.
    If learner_concept_mastery has no records despite passed submissions existing,
    authoritatively reconstructs mastery according to the deterministic scoring rules:
      - Clean pass without hints: +25%
      - Pass after hints: +15%
      - Failed submissions: +0%
      - Max clamped to 100%
      - Duplicate processing of the same submission cannot award mastery again.
    """
    with get_connection() as conn:
        # 1. Process any pending unprocessed submissions
        cur_unproc = conn.execute("""
            SELECT submission_id
            FROM submissions
            WHERE learner_id = ? AND processed_for_progress = 0
            ORDER BY rowid ASC
        """, (learner_id,))
        unprocessed_ids = [row["submission_id"] for row in cur_unproc.fetchall()]

    for sub_id in unprocessed_ids:
        process_submission_progress(sub_id)

    # 2. Check if mastery records exist in learner_concept_mastery
    with get_connection() as conn:
        cur_check = conn.execute("""
            SELECT COUNT(*) as cnt
            FROM learner_concept_mastery
            WHERE learner_id = ? AND mastery > 0
        """, (learner_id,))
        has_mastery = (cur_check.fetchone()["cnt"] > 0)

        # If no mastery recorded but there are passed submissions, reconstruct
        if not has_mastery:
            cur_passed = conn.execute("""
                SELECT challenge_id, MIN(hints_requested) as min_hints
                FROM submissions
                WHERE learner_id = ? AND all_passed = 1
                GROUP BY challenge_id
            """, (learner_id,))
            passed_rows = cur_passed.fetchall()

            if passed_rows:
                now_str = datetime.now(timezone.utc).isoformat()
                current_scores: dict[str, float] = {c: 0.0 for c in ALL_CONCEPTS}

                for prow in passed_rows:
                    cid = prow["challenge_id"].replace("-", "_")
                    ch_meta = CHALLENGE_BY_ID.get(cid)
                    if not ch_meta:
                        continue
                    delta = POINTS_PASS_NO_HINTS if prow["min_hints"] == 0 else POINTS_PASS_WITH_HINTS
                    for concept in ch_meta.get("tags", []):
                        if concept in current_scores:
                            current_scores[concept] = min(100.0, current_scores[concept] + delta)

                for concept, val in current_scores.items():
                    conn.execute("""
                        INSERT INTO learner_concept_mastery (learner_id, concept, mastery, updated_at)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(learner_id, concept) DO UPDATE SET
                            mastery = excluded.mastery,
                            updated_at = excluded.updated_at
                    """, (learner_id, concept, round(val, 1), now_str))
                conn.commit()


def get_learner_mastery(learner_id: str) -> dict[str, float]:
    """
    Return mastery dictionary for all known concepts.
    Concepts without recorded activity default to 0.0.
    """
    sync_learner_unprocessed_submissions(learner_id)

    mastery_map = {concept: 0.0 for concept in ALL_CONCEPTS}

    with get_connection() as conn:
        cur = conn.execute("""
            SELECT concept, mastery
            FROM learner_concept_mastery
            WHERE learner_id = ?
        """, (learner_id,))
        for row in cur.fetchall():
            concept = row["concept"].lower()
            if concept in mastery_map:
                mastery_map[concept] = float(row["mastery"])

    return mastery_map


def get_recurring_mistakes(learner_id: str) -> list[str]:
    """
    A mistake category is RECURRING if and only if it appears in failed
    submissions across at least two distinct challenge IDs.
    Failures on only one challenge NEVER qualify as recurring.
    """
    with get_connection() as conn:
        cur = conn.execute("""
            SELECT sm.category, s.challenge_id
            FROM submission_mistakes sm
            JOIN submissions s ON sm.submission_id = s.submission_id
            WHERE s.learner_id = ? AND s.all_passed = 0
        """, (learner_id,))

        category_challenges: dict[str, set[str]] = {}
        for row in cur.fetchall():
            cat = row["category"]
            cid = row["challenge_id"]
            if cat in REQUIRED_MISTAKE_CATEGORIES:
                category_challenges.setdefault(cat, set()).add(cid)

    recurring = [
        cat
        for cat, cids in category_challenges.items()
        if len(cids) >= 2
    ]
    return sorted(recurring)


def get_learner_progress_counts(learner_id: str) -> dict[str, Any]:
    """
    Return summary statistics of learner submissions and challenges completed.
    """
    with get_connection() as conn:
        cur_tot = conn.execute("""
            SELECT COUNT(*) as total_subs
            FROM submissions
            WHERE learner_id = ?
        """, (learner_id,))
        total_subs = cur_tot.fetchone()["total_subs"]

        cur_fails = conn.execute("""
            SELECT COUNT(*) as failed_subs
            FROM submissions
            WHERE learner_id = ? AND all_passed = 0
        """, (learner_id,))
        failed_subs = cur_fails.fetchone()["failed_subs"]

        cur_passed_cids = conn.execute("""
            SELECT DISTINCT challenge_id
            FROM submissions
            WHERE learner_id = ? AND all_passed = 1
        """, (learner_id,))
        passed_challenges = len(cur_passed_cids.fetchall())

        cur_attempted = conn.execute("""
            SELECT COUNT(DISTINCT challenge_id) as attempted_challenges
            FROM submissions
            WHERE learner_id = ?
        """, (learner_id,))
        attempted_challenges = cur_attempted.fetchone()["attempted_challenges"]

    pass_rate = round((passed_challenges / attempted_challenges * 100.0), 1) if attempted_challenges > 0 else 0.0

    return {
        "total_submissions": total_subs,
        "failed_submissions": failed_subs,
        "passed_challenges": passed_challenges,
        "total_attempted": attempted_challenges,
        "pass_rate_percent": pass_rate,
        "total_challenges": len(CHALLENGES),
    }


def get_passed_challenges(learner_id: str) -> set[str]:
    """Return set of challenge IDs that the learner has passed."""
    with get_connection() as conn:
        cur = conn.execute("""
            SELECT DISTINCT challenge_id
            FROM submissions
            WHERE learner_id = ? AND all_passed = 1
        """, (learner_id,))
        return {row["challenge_id"].replace("-", "_") for row in cur.fetchall()}


MISTAKE_HUMAN_NAMES = {
    "boundary_comparison": "Boundary Comparison",
    "off_by_one": "Off-by-One Error",
    "unhandled_short_input": "Unhandled Short Input",
    "mutates_input": "Mutates Input Argument",
    "print_not_return": "Print Instead of Return",
}


def get_learner_recent_activity(learner_id: str, limit: int = 5) -> list[dict[str, Any]]:
    """Return the most recent submissions for the learner from real SQLite data."""
    with get_connection() as conn:
        cur = conn.execute("""
            SELECT submission_id, challenge_id, all_passed, hints_requested, timestamp, summary
            FROM submissions
            WHERE learner_id = ?
            ORDER BY rowid DESC
            LIMIT ?
        """, (learner_id, limit))
        results = []
        for r in cur.fetchall():
            cid = r["challenge_id"]
            ch_meta = CHALLENGE_BY_ID.get(cid.replace("-", "_"), {})
            results.append({
                "submission_id": r["submission_id"],
                "challenge_id": cid,
                "challenge_title": ch_meta.get("title", cid),
                "all_passed": bool(r["all_passed"]),
                "hints_requested": r["hints_requested"],
                "timestamp": r["timestamp"],
                "summary": r["summary"] or "",
            })
        return results


def get_learner_mistake_details(learner_id: str) -> dict[str, Any]:
    """
    Return comprehensive evidence-based analysis of mistakes in failed submissions,
    differentiating recurring mistakes (failures across ≥ 2 distinct challenges)
    from single-challenge issues.
    """
    with get_connection() as conn:
        cur = conn.execute("""
            SELECT sm.category, sm.evidence, sm.confidence, s.challenge_id, s.timestamp
            FROM submission_mistakes sm
            JOIN submissions s ON sm.submission_id = s.submission_id
            WHERE s.learner_id = ? AND s.all_passed = 0
            ORDER BY s.rowid DESC
        """, (learner_id,))

        cat_data: dict[str, dict[str, Any]] = {}
        for row in cur.fetchall():
            cat = row["category"]
            cid = row["challenge_id"]
            if cat not in REQUIRED_MISTAKE_CATEGORIES:
                continue
            if cat not in cat_data:
                cat_data[cat] = {
                    "count": 0,
                    "challenges": set(),
                    "evidence_list": [],
                }
            cat_data[cat]["count"] += 1
            cat_data[cat]["challenges"].add(cid)
            if row["evidence"] and len(cat_data[cat]["evidence_list"]) < 3:
                cat_data[cat]["evidence_list"].append(row["evidence"])

    from recommendations import MISTAKE_TARGET_CHALLENGES

    passed_ids = get_passed_challenges(learner_id)
    all_affected_challenges = set()
    recurring_items = []
    other_items = []

    for cat, info in cat_data.items():
        cids = sorted(list(info["challenges"]))
        all_affected_challenges.update(cids)
        is_rec = len(cids) >= 2

        # Associated concepts across affected challenges
        concepts = set()
        ch_list = []
        for cid in cids:
            ch_meta = CHALLENGE_BY_ID.get(cid.replace("-", "_"), {})
            if ch_meta:
                ch_list.append({"id": ch_meta["id"], "title": ch_meta["title"], "difficulty": ch_meta.get("difficulty", "medium")})
                concepts.update(ch_meta.get("tags", []))

        # Target practice challenge
        target_ids = MISTAKE_TARGET_CHALLENGES.get(cat, [])
        practice_ch = None
        for tid in target_ids:
            if tid in CHALLENGE_BY_ID and tid not in passed_ids:
                meta = CHALLENGE_BY_ID[tid]
                practice_ch = {"id": meta["id"], "title": meta["title"], "difficulty": meta.get("difficulty", "easy")}
                break
        if not practice_ch and target_ids and target_ids[0] in CHALLENGE_BY_ID:
            meta = CHALLENGE_BY_ID[target_ids[0]]
            practice_ch = {"id": meta["id"], "title": meta["title"], "difficulty": meta.get("difficulty", "easy")}

        item = {
            "category_id": cat,
            "name": MISTAKE_HUMAN_NAMES.get(cat, cat),
            "is_recurring": is_rec,
            "failure_count": info["count"],
            "distinct_challenges_count": len(cids),
            "affected_challenges": ch_list,
            "concepts": sorted(list(concepts)),
            "evidence": info["evidence_list"],
            "priority": "High" if len(cids) >= 3 else ("Medium" if is_rec else "Low"),
            "practice_challenge": practice_ch,
        }

        if is_rec:
            recurring_items.append(item)
        else:
            other_items.append(item)

    recurring_items.sort(key=lambda x: (x["distinct_challenges_count"], x["failure_count"]), reverse=True)
    other_items.sort(key=lambda x: x["failure_count"], reverse=True)

    most_frequent_cat = recurring_items[0]["name"] if recurring_items else (other_items[0]["name"] if other_items else None)

    return {
        "recurring_categories_count": len(recurring_items),
        "affected_challenges_count": len(all_affected_challenges),
        "most_frequent_category": most_frequent_cat,
        "recurring": recurring_items,
        "all_categories": recurring_items + other_items,
    }


def create_exam_attempt(
    attempt_id: str,
    learner_id: str,
    challenge_id: str,
    duration_seconds: int,
) -> dict[str, Any]:
    """Create a new exam attempt with server-authoritative timestamps."""
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    deadline = now + timedelta(seconds=duration_seconds)
    start_iso = now.isoformat()
    deadline_iso = deadline.isoformat()

    with get_connection() as conn:
        conn.execute("""
            INSERT INTO exam_attempts (
                attempt_id, learner_id, challenge_id, start_time, deadline,
                duration_seconds, status, submitted_code, submitted_at, final_results, all_passed
            ) VALUES (?, ?, ?, ?, ?, ?, 'in_progress', NULL, NULL, NULL, 0)
        """, (attempt_id, learner_id, challenge_id, start_iso, deadline_iso, duration_seconds))
        conn.commit()

    return {
        "attempt_id": attempt_id,
        "learner_id": learner_id,
        "challenge_id": challenge_id,
        "start_time": start_iso,
        "deadline": deadline_iso,
        "duration_seconds": duration_seconds,
        "remaining_seconds": duration_seconds,
        "status": "in_progress",
        "all_passed": False,
    }


def get_exam_attempt(attempt_id: str) -> dict[str, Any] | None:
    """Retrieve an exam attempt and calculate authoritative remaining seconds."""
    with get_connection() as conn:
        cur = conn.execute("""
            SELECT * FROM exam_attempts WHERE attempt_id = ?
        """, (attempt_id,))
        row = cur.fetchone()
        if not row:
            return None

        attempt = dict(row)
        deadline_dt = datetime.fromisoformat(attempt["deadline"])
        now = datetime.now(timezone.utc)
        remaining = max(0, int((deadline_dt - now).total_seconds()))
        attempt["remaining_seconds"] = remaining

        # Auto-update status to expired if in_progress and time has elapsed
        if attempt["status"] == "in_progress" and remaining <= 0:
            exp_now = datetime.now(timezone.utc).isoformat()
            conn.execute("""
                UPDATE exam_attempts SET status = 'expired', submitted_at = ? WHERE attempt_id = ? AND status = 'in_progress'
            """, (exp_now, attempt_id))
            conn.commit()
            attempt["status"] = "expired"
            attempt["submitted_at"] = exp_now

        if attempt["final_results"]:
            try:
                attempt["final_results"] = json.loads(attempt["final_results"])
            except Exception:
                pass

        attempt["unlocked_hints"] = get_exam_hints(attempt_id)

        return attempt


def get_active_exam_attempt(learner_id: str, challenge_id: str) -> dict[str, Any] | None:
    """Find an active, unexpired attempt for learner and challenge to prevent accidental duplicates."""
    with get_connection() as conn:
        cur = conn.execute("""
            SELECT attempt_id FROM exam_attempts
            WHERE learner_id = ? AND challenge_id = ? AND status = 'in_progress'
            ORDER BY start_time DESC LIMIT 1
        """, (learner_id, challenge_id))
        row = cur.fetchone()
        if not row:
            return None
        return get_exam_attempt(row["attempt_id"])


def finalize_exam_attempt(
    attempt_id: str,
    submitted_code: str,
    final_results: dict[str, Any],
    all_passed: bool,
    is_expired: bool = False,
    submitted_at: str | None = None,
) -> bool:
    """
    Atomically finalize an exam attempt.
    Returns True if finalized, False if already finalized or expired.
    """
    now_iso = submitted_at or datetime.now(timezone.utc).isoformat()
    new_status = "expired" if is_expired else "submitted"
    results_json = json.dumps(final_results)

    with get_connection() as conn:
        cur = conn.execute("""
            UPDATE exam_attempts
            SET status = ?,
                submitted_code = ?,
                submitted_at = ?,
                final_results = ?,
                all_passed = ?
            WHERE attempt_id = ? AND status = 'in_progress'
        """, (new_status, submitted_code, now_iso, results_json, 1 if all_passed else 0, attempt_id))
        conn.commit()
        return cur.rowcount > 0


def record_exam_integrity_event(attempt_id: str, event_type: str, details: str = "") -> int:
    """Record an integrity event and return the total count of events for this attempt."""
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO exam_integrity_events (attempt_id, event_type, timestamp, details)
            VALUES (?, ?, ?, ?)
        """, (attempt_id, event_type, now_iso, details))
        conn.commit()

        cur = conn.execute("""
            SELECT COUNT(*) as cnt FROM exam_integrity_events WHERE attempt_id = ?
        """, (attempt_id,))
        return cur.fetchone()["cnt"]


def get_exam_integrity_events(attempt_id: str) -> list[dict[str, Any]]:
    """Retrieve all integrity events recorded for an attempt."""
    with get_connection() as conn:
        cur = conn.execute("""
            SELECT event_type, timestamp, details
            FROM exam_integrity_events
            WHERE attempt_id = ?
            ORDER BY id ASC
        """, (attempt_id,))
        return [dict(row) for row in cur.fetchall()]


def record_exam_hint(
    attempt_id: str,
    learner_id: str,
    challenge_id: str,
    hint_index: int,
    stage: str,
    hint_text: str,
    submission_id: str | None = None,
) -> dict[str, Any]:
    """Persist an unlocked examination hint."""
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO exam_hints (
                attempt_id, learner_id, challenge_id, hint_index, stage, hint_text, requested_at, submission_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (attempt_id, learner_id, challenge_id, hint_index, stage, hint_text, now_iso, submission_id))
        conn.commit()

    return {
        "hint_index": hint_index,
        "stage": stage,
        "hint_text": hint_text,
        "requested_at": now_iso,
    }


def get_exam_hints(attempt_id: str) -> list[dict[str, Any]]:
    """Retrieve all unlocked hints for an exam attempt in order."""
    with get_connection() as conn:
        cur = conn.execute("""
            SELECT hint_index, stage, hint_text, requested_at
            FROM exam_hints
            WHERE attempt_id = ?
            ORDER BY hint_index ASC
        """, (attempt_id,))
        rows = [dict(row) for row in cur.fetchall()]
        for r in rows:
            r["label"] = f"Hint {r['hint_index']} — {r['stage']}"
        return rows



# ---------------------------------------------------------------------------
# Authentication & User Management (Argon2id + Secure Sessions)
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Hash password using Argon2id with memory-hard scrypt fallback."""
    if _ph:
        return _ph.hash(password)
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=16384, r=8, p=1)
    return f"scrypt${salt.hex()}${derived.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against stored Argon2id or scrypt hash in constant time."""
    if not password_hash:
        return False
    if password_hash.startswith("$argon2"):
        if not _ph:
            return False
        try:
            return _ph.verify(password_hash, password)
        except (VerifyMismatchError, InvalidHash):
            return False
    elif password_hash.startswith("scrypt$"):
        parts = password_hash.split("$")
        if len(parts) != 3:
            return False
        try:
            salt = bytes.fromhex(parts[1])
            expected = bytes.fromhex(parts[2])
            derived = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=16384, r=8, p=1)
            return secrets.compare_digest(derived, expected)
        except Exception:
            return False
    return False


def create_user(full_name: str, email: str, password: str, age: int | None = None) -> dict[str, Any]:
    """
    Create a new user with normalized email and Argon2id password hash.
    Enforces uniqueness on email.
    """
    clean_name = full_name.strip()
    clean_email = email.strip().lower()
    if not clean_name:
        raise ValueError("Full name cannot be empty.")
    if not clean_email or "@" not in clean_email or "." not in clean_email:
        raise ValueError("A valid email address is required.")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")

    now_iso = datetime.now(timezone.utc).isoformat()
    p_hash = hash_password(password)
    user_id = f"usr_{secrets.token_hex(8)}"

    with get_connection() as conn:
        # Check uniqueness
        cur = conn.execute("SELECT user_id FROM users WHERE email = ?", (clean_email,))
        if cur.fetchone():
            raise ValueError("An account with this email address already exists.")

        conn.execute("""
            INSERT INTO users (user_id, full_name, email, password_hash, age, created_at, updated_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'active')
        """, (user_id, clean_name, clean_email, p_hash, age, now_iso, now_iso))
        conn.commit()

    return {
        "user_id": user_id,
        "full_name": clean_name,
        "email": clean_email,
        "age": age,
        "created_at": now_iso,
        "updated_at": now_iso,
        "status": "active",
    }


def get_user_by_email(email: str) -> dict[str, Any] | None:
    """Retrieve user record by normalized email, including password_hash for authentication."""
    clean_email = email.strip().lower()
    with get_connection() as conn:
        cur = conn.execute("SELECT * FROM users WHERE email = ?", (clean_email,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: str, include_hash: bool = False) -> dict[str, Any] | None:
    """Retrieve user record by user_id, omitting password_hash by default."""
    with get_connection() as conn:
        cur = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        if not row:
            return None
        res = dict(row)
        if not include_hash:
            res.pop("password_hash", None)
        return res


def update_user_profile(user_id: str, full_name: str | None = None, age: int | None = None) -> dict[str, Any] | None:
    """Update editable profile fields (full_name, age) and update timestamp."""
    user = get_user_by_id(user_id)
    if not user:
        return None

    new_name = full_name.strip() if full_name is not None else user["full_name"]
    if not new_name:
        raise ValueError("Full name cannot be empty.")
    new_age = age if age is not None else user.get("age")
    now_iso = datetime.now(timezone.utc).isoformat()

    with get_connection() as conn:
        conn.execute("""
            UPDATE users
            SET full_name = ?, age = ?, updated_at = ?
            WHERE user_id = ?
        """, (new_name, new_age, now_iso, user_id))
        conn.commit()

    return get_user_by_id(user_id)


def update_user_password(user_id: str, new_password: str) -> bool:
    """Update user password with freshly hashed Argon2id digest."""
    if len(new_password) < 8:
        raise ValueError("New password must be at least 8 characters long.")
    p_hash = hash_password(new_password)
    now_iso = datetime.now(timezone.utc).isoformat()

    with get_connection() as conn:
        cur = conn.execute("""
            UPDATE users
            SET password_hash = ?, updated_at = ?
            WHERE user_id = ?
        """, (p_hash, now_iso, user_id))
        conn.commit()
        return cur.rowcount > 0


def create_user_session(user_id: str, duration_days: int = 7) -> dict[str, Any]:
    """Create a new server-side session token stored in SQLite."""
    session_id = secrets.token_hex(32)
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=duration_days)

    with get_connection() as conn:
        conn.execute("""
            INSERT INTO user_sessions (session_id, user_id, created_at, expires_at, is_revoked)
            VALUES (?, ?, ?, ?, 0)
        """, (session_id, user_id, now.isoformat(), expires.isoformat()))
        conn.commit()

    return {
        "session_id": session_id,
        "user_id": user_id,
        "created_at": now.isoformat(),
        "expires_at": expires.isoformat(),
    }


def get_user_session(session_id: str) -> dict[str, Any] | None:
    """
    Validate active session. If session is revoked or expired, returns None.
    Returns session dict along with user profile.
    """
    if not session_id:
        return None

    now_iso = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cur = conn.execute("""
            SELECT s.session_id, s.user_id, s.created_at, s.expires_at, s.is_revoked,
                   u.full_name, u.email, u.age, u.created_at as user_created_at, u.status as user_status
            FROM user_sessions s
            JOIN users u ON s.user_id = u.user_id
            WHERE s.session_id = ? AND s.is_revoked = 0
        """, (session_id,))
        row = cur.fetchone()
        if not row:
            return None

        # Check expiration
        if row["expires_at"] < now_iso:
            conn.execute("UPDATE user_sessions SET is_revoked = 1 WHERE session_id = ?", (session_id,))
            conn.commit()
            return None

        return {
            "session_id": row["session_id"],
            "user_id": row["user_id"],
            "created_at": row["created_at"],
            "expires_at": row["expires_at"],
            "user": {
                "user_id": row["user_id"],
                "full_name": row["full_name"],
                "email": row["email"],
                "age": row["age"],
                "created_at": row["user_created_at"],
                "status": row["user_status"],
            }
        }


def revoke_user_session(session_id: str) -> bool:
    """Invalidate a specific session token."""
    with get_connection() as conn:
        cur = conn.execute("UPDATE user_sessions SET is_revoked = 1 WHERE session_id = ?", (session_id,))
        conn.commit()
        return cur.rowcount > 0


def revoke_all_user_sessions(user_id: str) -> int:
    """Invalidate all active sessions for a user."""
    with get_connection() as conn:
        cur = conn.execute("UPDATE user_sessions SET is_revoked = 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        return cur.rowcount


def get_user_learning_statistics(user_id: str) -> dict[str, Any]:
    """
    Aggregate authentic learning statistics for a specific user ID:
      • Total submissions, distinct passed challenges, distinct attempted challenges.
      • Concept mastery scores derived deterministically.
      • Recurring mistake patterns.
      • Recommended next challenge.
      • Examination attempts and passes.
    """
    from recommendations import get_recommendation

    with get_connection() as conn:
        # Total submissions
        sub_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM submissions WHERE learner_id = ?", (user_id,)
        ).fetchone()["cnt"]

        # Distinct passed challenges
        passed_count = conn.execute(
            "SELECT COUNT(DISTINCT challenge_id) as cnt FROM submissions WHERE learner_id = ? AND all_passed = 1", (user_id,)
        ).fetchone()["cnt"]

        # Distinct attempted challenges
        attempted_count = conn.execute(
            "SELECT COUNT(DISTINCT challenge_id) as cnt FROM submissions WHERE learner_id = ?", (user_id,)
        ).fetchone()["cnt"]

        # Exam statistics
        exam_total = conn.execute(
            "SELECT COUNT(*) as cnt FROM exam_attempts WHERE learner_id = ?", (user_id,)
        ).fetchone()["cnt"]

        exam_passed = conn.execute(
            "SELECT COUNT(*) as cnt FROM exam_attempts WHERE learner_id = ? AND all_passed = 1", (user_id,)
        ).fetchone()["cnt"]

    mastery = get_learner_mastery(user_id)
    recurring = get_recurring_mistakes(user_id)
    rec = get_recommendation(user_id)

    pass_rate = (passed_count / attempted_count * 100.0) if attempted_count > 0 else 0.0

    return {
        "user_id": user_id,
        "total_submissions": sub_count,
        "passed_challenges": passed_count,
        "passed_count": passed_count,
        "total_challenges": len(CHALLENGES),
        "attempted_challenges": attempted_count,
        "total_attempted": attempted_count,
        "pass_rate_percent": round(pass_rate, 1),
        "concept_mastery": mastery,
        "recurring_mistakes": recurring,
        "recommended_challenge": rec.get("recommended_challenge"),
        "recommendation_reason": rec.get("recommendation_reason", ""),
        "exam_attempts_count": exam_total,
        "exam_passed_count": exam_passed,
    }


# Initialize tables upon module import
init_db()

