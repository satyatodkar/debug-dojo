"""
storage.py  —  Debug Dojo Phase 4
=================================
In-memory and file-backed submission and hint tracking.
Associates submission ID with:
  - learner_id
  - challenge_id
  - code
  - all_passed
  - visible_tests
  - hidden_tests
  - mistakes
  - explanation
  - hint_ladder
  - current_hint_index
"""

import json
import os
from pathlib import Path
from typing import Any

STORAGE_FILE = Path(__file__).parent / "sandbox" / ".submissions.json"

# In-memory store
_SUBMISSIONS: dict[str, dict[str, Any]] = {}


def init_storage():
    """Load previously saved submissions if the file exists."""
    global _SUBMISSIONS
    if STORAGE_FILE.exists():
        try:
            with open(STORAGE_FILE, "r", encoding="utf-8") as f:
                _SUBMISSIONS = json.load(f)
        except Exception:
            _SUBMISSIONS = {}


def save_submission(sub_data: dict[str, Any]) -> None:
    """Store submission in memory and persist to disk."""
    sub_id = sub_data["submission_id"]
    _SUBMISSIONS[sub_id] = sub_data
    try:
        STORAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(_SUBMISSIONS, f, indent=2)
    except Exception:
        pass


def get_submission(submission_id: str) -> dict[str, Any] | None:
    """Retrieve submission record by ID."""
    return _SUBMISSIONS.get(submission_id)


def advance_hint(submission_id: str) -> dict[str, Any] | None:
    """
    Advance the hint position for a submission and return the next hint details.
    Returns None if the submission ID is unknown.
    """
    sub = _SUBMISSIONS.get(submission_id)
    if not sub:
        return None

    ladder = sub.get("hint_ladder", [])
    total_hints = len(ladder)

    # If all tests passed on this submission
    if sub.get("all_passed"):
        return {
            "submission_id": submission_id,
            "challenge_id": sub.get("challenge_id", ""),
            "status": "completed",
            "hint_number": 0,
            "total_hints": 0,
            "hint": None,
            "message": "All tests passed for this submission! No hints needed.",
            "has_more": False,
        }

    current_idx = sub.get("hint_index", 0)

    if current_idx >= total_hints:
        return {
            "submission_id": submission_id,
            "challenge_id": sub.get("challenge_id", ""),
            "status": "exhausted",
            "hint_number": total_hints,
            "total_hints": total_hints,
            "hint": None,
            "message": f"All {total_hints} hints have already been revealed for this submission. Try applying what you've learned to fix the issue!",
            "has_more": False,
        }

    hint_text = ladder[current_idx]
    next_idx = current_idx + 1
    sub["hint_index"] = next_idx
    save_submission(sub)

    return {
        "submission_id": submission_id,
        "challenge_id": sub.get("challenge_id", ""),
        "status": "active",
        "hint_number": next_idx,
        "total_hints": total_hints,
        "hint": hint_text,
        "has_more": next_idx < total_hints,
    }


# Initialize storage on module import
init_storage()
