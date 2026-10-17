"""
auth_utils.py — Debug Dojo Authentication Utilities & Dependencies
===================================================================
Provides:
  • Cookie and session configuration (HttpOnly, SameSite=Lax, dynamic Secure).
  • Current user dependency for FastAPI routes.
  • In-memory rate limiting for auth endpoints (brute-force deterrence).
  • CSRF origin verification on state-changing cookie requests.
"""

import os
import time
from collections import defaultdict
from fastapi import Request, HTTPException, status, Depends
from typing import Any

from database import get_user_session

SESSION_COOKIE_NAME = "dojo_session"
SESSION_MAX_AGE_DAYS = 7
SESSION_MAX_AGE_SECONDS = SESSION_MAX_AGE_DAYS * 24 * 60 * 60

# Rate limiter: tracks timestamps of requests per IP
_rate_limits: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_ATTEMPTS = 15  # 15 attempts per minute per IP


def check_rate_limit(request: Request, action: str = "auth") -> None:
    """Enforce rate limits per client IP on sensitive auth endpoints."""
    client_ip = request.client.host if request.client else "unknown"
    key = f"{action}:{client_ip}"
    now = time.time()

    # Clean old timestamps
    _rate_limits[key] = [t for t in _rate_limits[key] if now - t < RATE_LIMIT_WINDOW_SECONDS]

    if len(_rate_limits[key]) >= RATE_LIMIT_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Please wait a moment before trying again.",
        )

    _rate_limits[key].append(now)


def is_secure_cookie(request: Request) -> bool:
    """Determine whether the session cookie should have the Secure flag set."""
    env = os.environ.get("ENV", "development").lower()
    if env in ("production", "prod"):
        return True
    # If request was made over HTTPS
    if request.url.scheme == "https":
        return True
    proto = request.headers.get("x-forwarded-proto", "").lower()
    return proto == "https"


def verify_csrf(request: Request) -> None:
    """
    Validate Origin / Referer for state-changing cookie requests
    to protect against Cross-Site Request Forgery.
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return

    # If authenticated via cookie, check Origin or Referer
    if SESSION_COOKIE_NAME in request.cookies:
        origin = request.headers.get("origin")
        referer = request.headers.get("referer")
        host = request.headers.get("host")

        if origin:
            # Origin must match host
            origin_netloc = origin.split("://")[-1].rstrip("/")
            if host and origin_netloc != host and not host.startswith(origin_netloc):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cross-site request rejected (invalid Origin).",
                )
        elif referer:
            referer_netloc = referer.split("://")[-1].split("/")[0]
            if host and referer_netloc != host and not host.startswith(referer_netloc):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cross-site request rejected (invalid Referer).",
                )


def get_session_token(request: Request) -> str | None:
    """Extract session ID from HttpOnly cookie, or Authorization header fallback."""
    cookie_token = request.cookies.get(SESSION_COOKIE_NAME)
    if cookie_token:
        return cookie_token

    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()

    x_session = request.headers.get("x-session-id")
    if x_session:
        return x_session.strip()

    return None


async def get_current_user(request: Request) -> dict[str, Any]:
    """
    FastAPI dependency: require an authenticated user session.
    Derives identity strictly from server-side session token.
    Raises 401 if unauthenticated or session expired.
    """
    verify_csrf(request)

    token = get_session_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
        )

    session = get_user_session(token)
    if not session or not session.get("user"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired or was revoked. Please log in again.",
        )

    user = session["user"]
    user["session_id"] = session["session_id"]
    return user


async def get_optional_user(request: Request) -> dict[str, Any] | None:
    """
    FastAPI dependency: return user dict if authenticated, else None.
    Does not raise 401.
    """
    try:
        verify_csrf(request)
        token = get_session_token(request)
        if not token:
            return None
        session = get_user_session(token)
        if session and session.get("user"):
            user = session["user"]
            user["session_id"] = session["session_id"]
            return user
    except Exception:
        pass
    return None
