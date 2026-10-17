"""
routers/learner.py  —  Debug Dojo Phase 5
=========================================
Learner progress and recommendation API endpoints:
  • GET  /api/learner/{learner_id}  —  returns concept mastery, recurring mistakes,
                                       next recommended challenge & explanation.
  • POST /api/learner/update_progress —  idempotent progress update for a submission.
"""

from fastapi import APIRouter, HTTPException, status, Request
from pydantic import BaseModel, Field
from recommendations import get_recommendation
from database import (
    process_submission_progress,
    get_learner_mastery,
    get_learner_recent_activity,
    get_learner_mistake_details,
)
from auth_utils import get_optional_user

router = APIRouter(prefix="/api/learner", tags=["learner"])


class UpdateProgressRequest(BaseModel):
    submission_id: str = Field(..., min_length=1, max_length=100)


@router.get("/{learner_id}")
async def get_learner_profile(learner_id: str, request: Request):
    """
    Return concept mastery, recurring mistakes, next recommended challenge,
    recommendation explanation, progress metrics, recent activity, and mistake analysis.

    Validates learner ID format and enforces authorization on registered user IDs.
    """
    raw_id = learner_id.strip()
    if not raw_id or len(raw_id) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Learner ID must be a non-empty string under 100 characters.",
        )

    opt_user = await get_optional_user(request)
    if raw_id == "me":
        if not opt_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to view personal dashboard.",
            )
        cleaned_id = opt_user["user_id"]
    elif raw_id.startswith("usr_"):
        if not opt_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to view this user profile.",
            )
        if opt_user["user_id"] != raw_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to view another user's learning profile.",
            )
        cleaned_id = raw_id
    else:
        cleaned_id = raw_id

    rec = get_recommendation(cleaned_id)
    recent_act = get_learner_recent_activity(cleaned_id, limit=6)
    mistake_details = get_learner_mistake_details(cleaned_id)

    # Return structure matching the hackathon API contract with friendly aliases
    return {
        "learner_id": cleaned_id,
        "recurring_mistakes": rec["recurring_mistakes"],
        "mastery": rec["mastery"],
        "concept_mastery": {k.capitalize(): v for k, v in rec["mastery"].items()} | rec["mastery"],
        "next_recommended_challenge": rec["recommended_challenge"],
        "recommended_challenge": rec["recommended_challenge"],
        "recommended_challenge_id": (
            rec["recommended_challenge"]["id"]
            if rec["recommended_challenge"]
            else None
        ),
        "explanation": rec["recommendation_reason"],
        "recommendation_reason": rec["recommendation_reason"],
        "progress_counts": rec["progress_counts"],
        "recent_activity": recent_act,
        "mistake_analysis": mistake_details,
    }


@router.post("/update_progress")
async def update_progress_endpoint(req: UpdateProgressRequest):
    """
    Explicitly process progress updates for a submission.
    Idempotent: updates at most once even if called multiple times.
    """
    sub_id = req.submission_id.strip()
    applied = process_submission_progress(sub_id)
    return {
        "submission_id": sub_id,
        "applied": applied,
        "already_processed": not applied,
    }
