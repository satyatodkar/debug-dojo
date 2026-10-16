"""
routers/challenges.py  —  Debug Dojo Phase 2
=============================================
API routes for the challenge catalogue.

GET /api/challenges           → list of challenge summaries (id, title,
                                difficulty, tags) — no starter code, no tests.
GET /api/challenges/{id}      → full challenge detail: description,
                                starter_code, visible_tests.
                                NEVER returns hidden tests.
"""

from fastapi import APIRouter, HTTPException
from challenges import CHALLENGES, CHALLENGE_BY_ID

router = APIRouter(prefix="/api/challenges", tags=["challenges"])


# ---------------------------------------------------------------------------
# GET /api/challenges
# ---------------------------------------------------------------------------

@router.get("")
async def list_challenges():
    """
    Return a summary list of all challenges.

    Each item includes: id, title, difficulty, tags.
    Starter code, descriptions, and test cases are intentionally omitted
    to keep the payload small.
    """
    return [
        {
            "id":         ch["id"],
            "title":      ch["title"],
            "difficulty": ch["difficulty"],
            "tags":       ch["tags"],
        }
        for ch in CHALLENGES
    ]


# ---------------------------------------------------------------------------
# GET /api/challenges/{challenge_id}
# ---------------------------------------------------------------------------

@router.get("/{challenge_id}")
async def get_challenge(challenge_id: str):
    """
    Return the full detail for a single challenge.

    Includes: id, title, difficulty, tags, description, starter_code,
    and the VISIBLE tests only.

    Hidden tests are NEVER included in this response.
    Raises 404 if the challenge_id is unknown.
    """
    challenge = CHALLENGE_BY_ID.get(challenge_id)

    if challenge is None:
        raise HTTPException(
            status_code=404,
            detail=f"Challenge '{challenge_id}' not found. "
                   f"Call GET /api/challenges to see valid IDs.",
        )

    # Return a copy with only the fields the frontend needs.
    # Explicitly list keys so adding a backend-only field never leaks.
    return {
        "id":           challenge["id"],
        "title":        challenge["title"],
        "difficulty":   challenge["difficulty"],
        "tags":         challenge["tags"],
        "description":  challenge["description"],
        "starter_code": challenge["starter_code"],
        "visible_tests": [
            {
                "label": t["label"],
                "call": t["call"],
                "expected": t["expected"],
            }
            for t in challenge["visible_tests"]
        ],
    }
