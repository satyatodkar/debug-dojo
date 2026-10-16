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
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

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

            CREATE INDEX IF NOT EXISTS idx_submissions_learner ON submissions(learner_id);
            CREATE INDEX IF NOT EXISTS idx_submissions_challenge ON submissions(challenge_id);
            CREATE INDEX IF NOT EXISTS idx_mistakes_sub ON submission_mistakes(submission_id);
            CREATE INDEX IF NOT EXISTS idx_mistakes_cat ON submission_mistakes(category);
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
            delta = POINTS_FAIL_PENALTY            # -5.0

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


def get_learner_mastery(learner_id: str) -> dict[str, float]:
    """
    Return mastery dictionary for all known concepts.
    Concepts without recorded activity default to 0.0.
    """
    mastery_map = {concept: 0.0 for concept in ALL_CONCEPTS}

    with get_connection() as conn:
        cur = conn.execute("""
            SELECT concept, mastery
            FROM learner_concept_mastery
            WHERE learner_id = ?
        """, (learner_id,))
        for row in cur.fetchall():
            concept = row["concept"]
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


def get_learner_progress_counts(learner_id: str) -> dict[str, int]:
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

    return {
        "total_submissions": total_subs,
        "failed_submissions": failed_subs,
        "passed_challenges": passed_challenges,
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


# Initialize tables upon module import
init_db()
