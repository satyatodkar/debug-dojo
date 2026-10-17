"""
routers/auth.py — Debug Dojo Authentication Endpoints
=====================================================
Implements:
  • POST /api/auth/signup — validate and register a new learner account.
  • POST /api/auth/login  — authenticate credentials and set secure HttpOnly cookie.
  • POST /api/auth/logout — revoke session and clear cookie.
  • GET  /api/auth/me     — return current authenticated user profile.
"""

import re
from fastapi import APIRouter, HTTPException, status, Request, Response, Depends
from pydantic import BaseModel, Field, field_validator
from typing import Optional

from database import (
    create_user,
    get_user_by_email,
    verify_password,
    create_user_session,
    revoke_user_session,
)
from auth_utils import (
    SESSION_COOKIE_NAME,
    SESSION_MAX_AGE_SECONDS,
    is_secure_cookie,
    check_rate_limit,
    get_session_token,
    get_current_user,
)

router = APIRouter(prefix="/api/auth", tags=["authentication"])

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

# ── Pydantic Request Models ───────────────────────────────────────────────────

class SignupRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)
    age: Optional[int] = Field(default=None, ge=5, le=130)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        clean = v.strip().lower()
        if not EMAIL_REGEX.match(clean):
            raise ValueError("Invalid email address format.")
        return clean


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        clean = v.strip().lower()
        if not EMAIL_REGEX.match(clean):
            raise ValueError("Invalid email address format.")
        return clean


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(req: SignupRequest, request: Request, response: Response):
    """
    Register a new learner account with Argon2id password hashing.
    Enforces password confirmation, email normalization, and uniqueness.
    Automatically establishes a server-side session.
    """
    check_rate_limit(request, "signup")

    if req.password != req.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match.",
        )

    try:
        user = create_user(
            full_name=req.full_name,
            email=str(req.email),
            password=req.password,
            age=req.age,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Automatically log the user in
    session = create_user_session(user["user_id"])
    secure_flag = is_secure_cookie(request)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session["session_id"],
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=secure_flag,
        path="/",
    )

    return {
        "status": "ok",
        "message": "Account created successfully.",
        "user": user,
    }


@router.post("/login")
async def login(req: LoginRequest, request: Request, response: Response):
    """
    Authenticate user credentials against Argon2id hash.
    Sets HttpOnly session cookie on success.
    Uses generic error message to prevent account enumeration.
    """
    check_rate_limit(request, "login")

    clean_email = str(req.email).strip().lower()
    user_record = get_user_by_email(clean_email)

    # Constant-time comparison / verification
    if not user_record or not verify_password(req.password, user_record.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if user_record.get("status") != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is suspended or deactivated.",
        )

    # Create server session
    session = create_user_session(user_record["user_id"])
    secure_flag = is_secure_cookie(request)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session["session_id"],
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=secure_flag,
        path="/",
    )

    safe_user = {
        "user_id": user_record["user_id"],
        "full_name": user_record["full_name"],
        "email": user_record["email"],
        "age": user_record.get("age"),
        "created_at": user_record["created_at"],
        "status": user_record["status"],
    }

    return {
        "status": "ok",
        "message": "Login successful.",
        "user": safe_user,
    }


@router.post("/logout")
async def logout(request: Request, response: Response):
    """
    Invalidate active server session and clear the HttpOnly session cookie.
    """
    token = get_session_token(request)
    if token:
        revoke_user_session(token)

    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
    )

    return {
        "status": "ok",
        "message": "Logged out successfully.",
    }


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    """
    Return currently authenticated user's profile.
    Derives identity strictly from server-side session.
    """
    return {
        "status": "ok",
        "user": user,
        "user_id": user.get("user_id"),
        "full_name": user.get("full_name"),
        "email": user.get("email"),
        "age": user.get("age"),
        "created_at": user.get("created_at"),
        "status_code_name": user.get("status"),
    }
