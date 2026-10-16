"""
routers/hints.py  —  Debug Dojo Phase 4
======================================
POST /api/hint  —  Retrieves progressive, multi-tiered hints for a submission.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from storage import advance_hint, get_submission
from database import increment_submission_hint

router = APIRouter(prefix="/api", tags=["hints"])


class HintRequest(BaseModel):
    submission_id: str = Field(..., min_length=1, max_length=100)


@router.post("/hint")
async def get_next_hint(req: HintRequest):
    """
    Return the next progressive hint for a given submission ID.
    Handles active hints, exhausted hint ladders, successful submissions,
    and unknown submission IDs (404).
    """
    sub_id = req.submission_id.strip()
    result = advance_hint(sub_id)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Submission '{sub_id}' not found. Please submit your code first.",
        )

    if result.get("status") == "active":
        increment_submission_hint(sub_id)

    return result
