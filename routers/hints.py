"""
routers/hints.py  —  Debug Dojo Phase 4 & Phase 7
================================================
POST /api/hint  —  Retrieves progressive, multi-tiered hints for a submission
                   or an active examination attempt.
"""

from typing import Any
from fastapi import APIRouter, HTTPException, status, Request
from pydantic import BaseModel, Field
from storage import advance_hint, get_submission
from database import (
    increment_submission_hint,
    get_exam_attempt,
    record_exam_hint,
    get_exam_hints,
)
from auth_utils import get_optional_user
from hint_engine import CHALLENGE_DEFAULT_LADDERS, build_hint_ladder
from challenges import CHALLENGE_BY_ID

router = APIRouter(prefix="/api", tags=["hints"])


class HintRequest(BaseModel):
    submission_id: str | None = Field(default=None, max_length=100)
    attempt_id: str | None = Field(default=None, max_length=100)
    challenge_id: str | None = Field(default=None, max_length=100)
    learner_id: str | None = Field(default=None, max_length=100)


def verify_attempt_access(attempt: dict[str, Any], opt_user: dict[str, Any] | None) -> None:
    """Enforce user authorization on examination attempts."""
    owner_id = attempt.get("learner_id", "")
    if opt_user:
        if owner_id.startswith("usr_") and owner_id != opt_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to access another user's examination attempt.",
            )
    elif owner_id.startswith("usr_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to access this examination attempt.",
        )


async def process_exam_hint(
    attempt_id: str,
    request: Request,
    learner_id: str | None = None,
    submission_id: str | None = None,
    challenge_id: str | None = None,
) -> dict[str, Any]:
    """
    Validate exam attempt, ownership, authoritative deadline, and issue the next progressive hint.
    """
    attempt = get_exam_attempt(attempt_id)
    if not attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Examination attempt '{attempt_id}' not found.",
        )

    opt_user = await get_optional_user(request)
    verify_attempt_access(attempt, opt_user)

    if learner_id and learner_id != attempt.get("learner_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this examination attempt.",
        )

    # Validate active exam attempt and time remaining
    if attempt.get("status") != "in_progress" or attempt.get("remaining_seconds", 0) <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot request hints: examination time has expired or attempt is finalized.",
        )

    unlocked = get_exam_hints(attempt_id)
    total_unlocked = len(unlocked)

    if total_unlocked >= 3:
        return {
            "status": "exhausted",
            "attempt_id": attempt_id,
            "challenge_id": attempt["challenge_id"],
            "hint_number": 3,
            "total_hints": 3,
            "hint": None,
            "message": "All 3 progressive hints have already been unlocked for this examination. Try applying what you've learned!",
            "has_more": False,
            "unlocked_hints": unlocked,
        }

    next_idx = total_unlocked + 1
    stage_names = ["Think", "Investigate", "Narrow it down"]
    stage_name = stage_names[next_idx - 1]
    stage_label = f"Hint {next_idx} — {stage_name}"

    cid = (challenge_id or attempt["challenge_id"]).replace("-", "_")
    ladder = None
    if submission_id:
        sub = get_submission(submission_id.strip())
        if sub:
            ch = CHALLENGE_BY_ID.get(cid) or {}
            ladder = build_hint_ladder(
                ch,
                sub.get("mistakes", []),
                sub.get("visible_results", []),
                sub.get("hidden_results", []),
            )

    if not ladder:
        ladder = CHALLENGE_DEFAULT_LADDERS.get(cid)

    if not ladder:
        ladder = [
            "What specific requirement from the challenge description is the failing test checking?",
            "Compare the expected output with your function's actual output for the first visible test case.",
            "Walk through your function step-by-step with the input to identify where the logic diverges from the specification.",
        ]

    hint_text = ladder[next_idx - 1]

    # Record unlocked hint
    record_exam_hint(
        attempt_id=attempt_id,
        learner_id=attempt["learner_id"],
        challenge_id=attempt["challenge_id"],
        hint_index=next_idx,
        stage=stage_name,
        hint_text=hint_text,
        submission_id=submission_id,
    )

    all_unlocked = get_exam_hints(attempt_id)

    return {
        "status": "active",
        "attempt_id": attempt_id,
        "challenge_id": attempt["challenge_id"],
        "hint_number": next_idx,
        "total_hints": 3,
        "stage": stage_name,
        "label": stage_label,
        "hint": hint_text,
        "has_more": next_idx < 3,
        "unlocked_hints": all_unlocked,
    }


@router.post("/hint")
async def get_next_hint(req: HintRequest, request: Request):
    """
    Return the next progressive hint for a given submission ID or examination attempt.
    Supports practice mode submissions as well as in-exam hints.
    """
    if req.attempt_id:
        return await process_exam_hint(
            attempt_id=req.attempt_id.strip(),
            request=request,
            learner_id=req.learner_id.strip() if req.learner_id else None,
            submission_id=req.submission_id.strip() if req.submission_id else None,
            challenge_id=req.challenge_id.strip() if req.challenge_id else None,
        )

    sub_id = (req.submission_id or "").strip()
    if not sub_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either submission_id or attempt_id must be provided to request a hint.",
        )

    result = advance_hint(sub_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Submission '{sub_id}' not found. Please submit your code first.",
        )

    if result.get("status") == "active":
        increment_submission_hint(sub_id)

    return result
