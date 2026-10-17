"""
routers/account.py — Debug Dojo Account & Profile Management Endpoints
======================================================================
Implements:
  • GET   /api/account                — return personal profile & authentic learning stats.
  • PATCH /api/account                — update permitted profile fields (full_name, age).
  • POST  /api/account/change-password — safely update password with current verification.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import Optional

from auth_utils import get_current_user
from database import (
    get_user_by_id,
    get_user_learning_statistics,
    update_user_profile,
    update_user_password,
    verify_password,
)

router = APIRouter(prefix="/api/account", tags=["account"])


# ── Pydantic Request Models ───────────────────────────────────────────────────

class UpdateAccountRequest(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    age: Optional[int] = Field(default=None, ge=5, le=130)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_new_password: str = Field(..., min_length=8, max_length=128)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("")
async def get_account(user: dict = Depends(get_current_user)):
    """
    Return current authenticated user's personal information and
    authentic learning statistics derived from their actual activity.
    """
    user_id = user["user_id"]
    profile = get_user_by_id(user_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account not found.",
        )

    stats = get_user_learning_statistics(user_id)

    return {
        "status": "ok",
        "user": profile,
        "statistics": stats,
    }


@router.patch("")
async def update_account(req: UpdateAccountRequest, user: dict = Depends(get_current_user)):
    """
    Validate and update permitted profile fields (full_name, age).
    Email remains read-only for account integrity.
    """
    user_id = user["user_id"]
    try:
        updated = update_user_profile(
            user_id=user_id,
            full_name=req.full_name,
            age=req.age,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account not found.",
        )

    return {
        "status": "ok",
        "message": "Profile updated successfully.",
        "user": updated,
    }


@router.post("/change-password")
async def change_password(req: ChangePasswordRequest, user: dict = Depends(get_current_user)):
    """
    Safely update user's password with verification of current password.
    Never exposes current or new password in responses or logs.
    """
    user_id = user["user_id"]
    user_record = get_user_by_id(user_id, include_hash=True)
    if not user_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account not found.",
        )

    if not verify_password(req.current_password, user_record.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password.",
        )

    if req.new_password != req.confirm_new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New passwords do not match.",
        )

    try:
        update_user_password(user_id, req.new_password)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return {
        "status": "ok",
        "message": "Password updated successfully.",
    }
