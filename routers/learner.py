"""
routers/learner.py  —  Debug Dojo Phase 5
=========================================
Learner progress and recommendation API endpoints:
  • GET  /api/learner/{learner_id}  —  returns concept mastery, recurring mistakes,
                                       next recommended challenge & explanation.
  • POST /api/learner/update_progress —  idempotent progress update for a submission.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from recommendations import get_recommendation
from database import process_submission_progress, get_learner_mastery

router = APIRouter(prefix="/api/learner", tags=["learner"])


class UpdateProgressRequest(BaseModel):
    submission_id: str = Field(..., min_length=1, max_length=100)


@router.get("/{learner_id}")
async def get_learner_profile(learner_id: str):
    """
    Return concept mastery, recurring mistakes, next recommended challenge,
    recommendation explanation, and progress metrics for a pseudonymous learner.

    Validates learner ID format. Returns clean default starter state for new learners.
    """
    cleaned_id = learner_id.strip()
    if not cleaned_id or len(cleaned_id) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Learner ID must be a non-empty string under 100 characters.",
        )

    rec = get_recommendation(cleaned_id)

    # Return structure matching the hackathon API contract with friendly aliases
    return {
        "learner_id": cleaned_id,
        "recurring_mistakes": rec["recurring_mistakes"],
        "mastery": rec["mastery"],
        "concept_mastery": rec["mastery"],
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
