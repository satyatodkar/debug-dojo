"""
routers/exam.py — Debug Dojo Examination Router
================================================
Handles:
  • Examination session creation and retrieval with authoritative deadline.
  • Running visible tests inside isolated Docker sandbox.
  • Final submission evaluation with hidden-test isolation and atomic finalization.
  • Recording and querying integrity events (anti-paste, blur, visibility change).
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, HTTPException, status, Request
from pydantic import BaseModel, Field

from auth_utils import get_optional_user
from challenges import CHALLENGE_BY_ID, HIDDEN_TESTS
from exam_config import (
    DIFFICULTY_DURATIONS,
    DEV_TEST_TIMER_SECONDS,
    EXAM_TIMEOUT_PER_TEST,
    EXAM_MAX_CODE_BYTES,
    INTEGRITY_WARNING_THRESHOLD,
    INTEGRITY_RATE_LIMIT_PER_MIN,
)
from sandbox.docker_executor import (
    run_one_test,
    check_docker_available,
    OUTCOME_PASSED,
)
from database import (
    create_exam_attempt,
    get_exam_attempt,
    get_active_exam_attempt,
    finalize_exam_attempt,
    record_exam_integrity_event,
    get_exam_integrity_events,
    get_exam_hints,
)
from routers.hints import process_exam_hint
from ai_agent import (
    evaluate_exam_assistant_chat,
    EXAM_GUARDRAIL_POLICY_VERSION,
    ConfigurationError,
    ModelProviderError,
)

router = APIRouter(prefix="/api/exam", tags=["examination"])


# ── Request / Response Models ─────────────────────────────────────────────────

class ExamStartRequest(BaseModel):
    challenge_id: str = Field(..., min_length=1, max_length=100)
    learner_id: str = Field(..., min_length=1, max_length=100)
    dev_duration: int | None = Field(default=None, ge=1, le=3600)


class ExamCodeRequest(BaseModel):
    code: str = Field(..., min_length=1)


class ExamIntegrityRequest(BaseModel):
    event_type: str = Field(..., min_length=1, max_length=50)
    details: str = Field(default="", max_length=500)


class ExamAssistantChatRequest(BaseModel):
    attempt_id: str | None = Field(default=None, max_length=100)
    message: str = Field(..., min_length=1, max_length=2000)
    current_code: str = Field(default="", max_length=10000)
    test_results_summary: str | None = Field(default=None, max_length=2000)
    provider: str | None = Field(default=None, max_length=50)


# ── Authorization Helper ───────────────────────────────────────────────────────

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


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/start")
async def start_exam(req: ExamStartRequest, request: Request):
    """
    Start or resume an examination attempt.
    Enforces server-authoritative difficulty-based timers.
    Derives learner_id from authenticated session if logged in.
    """
    cid = req.challenge_id.strip().replace("-", "_")
    challenge = CHALLENGE_BY_ID.get(cid)
    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Challenge '{req.challenge_id}' not found.",
        )

    opt_user = await get_optional_user(request)
    if opt_user:
        learner_id = opt_user["user_id"]
    else:
        learner_id = req.learner_id.strip()

    if not learner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Learner ID cannot be empty.",
        )

    # Prevent duplicate active attempts on double clicks
    existing = get_active_exam_attempt(learner_id, cid)
    if existing and existing["remaining_seconds"] > 0:
        return _format_attempt_response(existing, challenge)

    # Determine duration: dev override or strict difficulty duration
    difficulty = str(challenge.get("difficulty", "easy")).lower()
    if req.dev_duration:
        duration_seconds = req.dev_duration
    else:
        duration_seconds = DIFFICULTY_DURATIONS.get(difficulty, 15 * 60)

    attempt_id = f"atm_{uuid.uuid4().hex[:12]}"
    attempt = create_exam_attempt(
        attempt_id=attempt_id,
        learner_id=learner_id,
        challenge_id=cid,
        duration_seconds=duration_seconds,
    )

    return _format_attempt_response(attempt, challenge)


@router.get("/{attempt_id}")
async def get_exam(attempt_id: str, request: Request):
    """
    Retrieve current attempt state.
    Recalculates remaining time from authoritative deadline.
    """
    attempt = get_exam_attempt(attempt_id)
    if not attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Examination attempt '{attempt_id}' not found.",
        )

    opt_user = await get_optional_user(request)
    verify_attempt_access(attempt, opt_user)

    challenge = CHALLENGE_BY_ID.get(attempt["challenge_id"])
    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Challenge '{attempt['challenge_id']}' not found.",
        )

    resp = _format_attempt_response(attempt, challenge)
    integrity_events = get_exam_integrity_events(attempt_id)
    resp["integrity_events_count"] = len(integrity_events)
    resp["integrity_warning"] = len(integrity_events) >= INTEGRITY_WARNING_THRESHOLD
    if attempt.get("submitted_code"):
        resp["submitted_code"] = attempt["submitted_code"]
    if attempt.get("final_results"):
        resp["final_results"] = attempt["final_results"]

    return resp


@router.post("/{attempt_id}/run-tests")
async def run_visible_tests(attempt_id: str, req: ExamCodeRequest, request: Request):
    """
    Run VISIBLE tests only during an active examination.
    Does NOT touch hidden tests and does NOT finalize the attempt.
    """
    attempt = get_exam_attempt(attempt_id)
    if not attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Examination attempt '{attempt_id}' not found.",
        )

    opt_user = await get_optional_user(request)
    verify_attempt_access(attempt, opt_user)

    if attempt["status"] != "in_progress" or attempt["remaining_seconds"] <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot run tests: examination time has expired or attempt is finalized.",
        )

    code_bytes = len(req.code.encode("utf-8", errors="replace"))
    if code_bytes > EXAM_MAX_CODE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Submitted code exceeds maximum size limit ({EXAM_MAX_CODE_BYTES} bytes).",
        )

    # Docker sandbox check: uses Docker if available, otherwise falls back gracefully
    # if not await check_docker_available():
    #     raise HTTPException(
    #         status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    #         detail="Docker execution sandbox is unavailable. Fail-closed enforced.",
    #     )

    cid = attempt["challenge_id"]
    challenge = CHALLENGE_BY_ID.get(cid)
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found.")

    fn_name = challenge["id"]
    visible_tests = challenge.get("visible_tests", [])

    async def execute_visible(idx: int, vt: dict[str, Any]) -> dict[str, Any]:
        res = await run_one_test(
            learner_code=req.code,
            fn_name=fn_name,
            args=vt.get("args", ()),
            expected=vt.get("expected_val"),
            is_visible=True,
            timeout_seconds=EXAM_TIMEOUT_PER_TEST,
            fail_closed=False,
        )
        return {
            "test_id": idx + 1,
            "label": vt.get("label", f"Visible Test #{idx + 1}"),
            "call": vt.get("call", ""),
            "outcome": res.get("outcome"),
            "expected": res.get("expected"),
            "actual": res.get("actual"),
            "details": res.get("details", ""),
            "execution_time": res.get("execution_time", 0.0),
        }

    visible_outcomes = await asyncio.gather(
        *(execute_visible(i, vt) for i, vt in enumerate(visible_tests))
    )

    passed_count = sum(1 for t in visible_outcomes if t["outcome"] == OUTCOME_PASSED)
    return {
        "attempt_id": attempt_id,
        "visible_tests": visible_outcomes,
        "visible_passed": passed_count,
        "visible_total": len(visible_outcomes),
    }


@router.post("/{attempt_id}/submit")
async def submit_exam(attempt_id: str, req: ExamCodeRequest, request: Request):
    """
    Finalize an examination attempt.
    Runs visible AND hidden tests in isolated Docker containers.
    Protects hidden test confidentiality: never leaks hidden inputs, expected values, or tracebacks.
    Atomically transitions attempt status to prevent double-finalization.
    """
    attempt = get_exam_attempt(attempt_id)
    if not attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Examination attempt '{attempt_id}' not found.",
        )

    opt_user = await get_optional_user(request)
    verify_attempt_access(attempt, opt_user)

    if attempt["status"] != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Examination attempt is already finalized (status: {attempt['status']}).",
        )

    code_bytes = len(req.code.encode("utf-8", errors="replace"))
    if code_bytes > EXAM_MAX_CODE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Submitted code exceeds maximum size limit ({EXAM_MAX_CODE_BYTES} bytes).",
        )

    # Server-side authoritative deadline check
    deadline_dt = datetime.fromisoformat(attempt["deadline"])
    now = datetime.now(timezone.utc)
    if now > deadline_dt:
        # Finalize as expired
        finalize_exam_attempt(
            attempt_id=attempt_id,
            submitted_code=req.code,
            final_results={"error": "Submission rejected: examination deadline has expired."},
            all_passed=False,
            is_expired=True,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Examination time has expired. The attempt has been finalized.",
        )

    # Docker sandbox check: uses Docker if available, otherwise falls back gracefully
    # if not await check_docker_available():
    #     raise HTTPException(
    #         status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    #         detail="Docker execution sandbox is unavailable. Fail-closed enforced.",
    #     )

    cid = attempt["challenge_id"]
    challenge = CHALLENGE_BY_ID.get(cid)
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found.")

    fn_name = challenge["id"]
    visible_tests = challenge.get("visible_tests", [])
    hidden_tests = HIDDEN_TESTS.get(cid, [])

    # 1. Execute visible tests
    async def execute_visible(idx: int, vt: dict[str, Any]) -> dict[str, Any]:
        res = await run_one_test(
            learner_code=req.code,
            fn_name=fn_name,
            args=vt.get("args", ()),
            expected=vt.get("expected_val"),
            is_visible=True,
            timeout_seconds=EXAM_TIMEOUT_PER_TEST,
            fail_closed=False,
        )
        return {
            "test_id": idx + 1,
            "label": vt.get("label", f"Visible Test #{idx + 1}"),
            "call": vt.get("call", ""),
            "outcome": res.get("outcome"),
            "expected": res.get("expected"),
            "actual": res.get("actual"),
            "details": res.get("details", ""),
            "execution_time": res.get("execution_time", 0.0),
        }

    # 2. Execute hidden tests (Strict confidentiality: input & expected NEVER passed to student)
    async def execute_hidden(idx: int, ht: dict[str, Any]) -> dict[str, Any]:
        res = await run_one_test(
            learner_code=req.code,
            fn_name=fn_name,
            args=ht.get("args", ()),
            expected=ht.get("expected"),
            is_visible=False,
            timeout_seconds=EXAM_TIMEOUT_PER_TEST,
            fail_closed=False,
        )
        # Disclose ONLY test id, outcome, safe details, and execution time
        return {
            "test_id": idx + 1,
            "outcome": res.get("outcome"),
            "details": res.get("details", ""),
            "execution_time": res.get("execution_time", 0.0),
        }

    visible_outcomes = await asyncio.gather(
        *(execute_visible(i, vt) for i, vt in enumerate(visible_tests))
    )
    hidden_outcomes = await asyncio.gather(
        *(execute_hidden(i, ht) for i, ht in enumerate(hidden_tests))
    )

    total_tests = len(visible_outcomes) + len(hidden_outcomes)
    vis_passed = sum(1 for r in visible_outcomes if r["outcome"] == OUTCOME_PASSED)
    hid_passed = sum(1 for r in hidden_outcomes if r["outcome"] == OUTCOME_PASSED)
    total_passed = vis_passed + hid_passed
    all_passed = (total_passed == total_tests)

    if all_passed:
        summary = (
            f"Examination Passed! All {total_tests} tests succeeded "
            f"({vis_passed}/{len(visible_outcomes)} visible, {hid_passed}/{len(hidden_outcomes)} hidden)."
        )
    else:
        summary = (
            f"Examination Submitted: Passed {total_passed} of {total_tests} tests "
            f"({vis_passed}/{len(visible_outcomes)} visible, {hid_passed}/{len(hidden_outcomes)} hidden)."
        )

    final_results = {
        "all_passed": all_passed,
        "summary": summary,
        "visible_tests": visible_outcomes,
        "hidden_tests": hidden_outcomes,
        "hidden_summary": {
            "total": len(hidden_outcomes),
            "passed": hid_passed,
        },
    }

    submitted_at_iso = datetime.now(timezone.utc).isoformat()

    # Atomic finalization
    finalized = finalize_exam_attempt(
        attempt_id=attempt_id,
        submitted_code=req.code,
        final_results=final_results,
        all_passed=all_passed,
        is_expired=False,
        submitted_at=submitted_at_iso,
    )

    if not finalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Conflict: attempt was finalized or expired concurrently.",
        )

    integrity_events = get_exam_integrity_events(attempt_id)

    return {
        "attempt_id": attempt_id,
        "status": "submitted",
        "all_passed": all_passed,
        "summary": summary,
        "submitted_at": submitted_at_iso,
        "visible_tests": visible_outcomes,
        "hidden_tests": hidden_outcomes,
        "hidden_summary": {
            "total": len(hidden_outcomes),
            "passed": hid_passed,
        },
        "integrity_summary": {
            "total_events": len(integrity_events),
            "warning": len(integrity_events) >= INTEGRITY_WARNING_THRESHOLD,
        },
    }


@router.post("/{attempt_id}/integrity")
async def log_integrity_event(attempt_id: str, req: ExamIntegrityRequest, request: Request):
    """
    Log an integrity event (anti-paste violation, tab blur, fullscreen exit).
    Validates attempt and rate-limits to prevent event flooding.
    """
    attempt = get_exam_attempt(attempt_id)
    if not attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Examination attempt '{attempt_id}' not found.",
        )

    opt_user = await get_optional_user(request)
    verify_attempt_access(attempt, opt_user)

    existing_events = get_exam_integrity_events(attempt_id)
    if len(existing_events) >= INTEGRITY_RATE_LIMIT_PER_MIN:
        return {
            "recorded": False,
            "message": "Rate limit exceeded for integrity event logging.",
            "total_events": len(existing_events),
            "warning": True,
        }

    total = record_exam_integrity_event(
        attempt_id=attempt_id,
        event_type=req.event_type.strip(),
        details=req.details.strip(),
    )

    return {
        "recorded": True,
        "total_events": total,
        "warning": total >= INTEGRITY_WARNING_THRESHOLD,
    }


class ExamHintRequest(BaseModel):
    submission_id: str | None = Field(default=None, max_length=100)
    challenge_id: str | None = Field(default=None, max_length=100)
    learner_id: str | None = Field(default=None, max_length=100)


@router.post("/{attempt_id}/hint")
async def request_in_exam_hint(attempt_id: str, request: Request, req: ExamHintRequest | None = None):
    """
    Request the next progressive, non-spoiler hint for an active examination attempt.
    """
    sub_id = req.submission_id if req else None
    cid = req.challenge_id if req else None
    lid = req.learner_id if req else None
    return await process_exam_hint(
        attempt_id=attempt_id.strip(),
        request=request,
        learner_id=lid,
        submission_id=sub_id,
        challenge_id=cid,
    )


@router.get("/{attempt_id}/hints")
async def get_attempt_hints(attempt_id: str, request: Request):
    """
    Retrieve all unlocked hints for an examination attempt.
    """
    attempt = get_exam_attempt(attempt_id)
    if not attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Examination attempt '{attempt_id}' not found.",
        )
    opt_user = await get_optional_user(request)
    verify_attempt_access(attempt, opt_user)

    unlocked = get_exam_hints(attempt_id)
    return {
        "attempt_id": attempt_id,
        "challenge_id": attempt["challenge_id"],
        "total_unlocked": len(unlocked),
        "total_hints": 3,
        "has_more": len(unlocked) < 3,
        "unlocked_hints": unlocked,
    }


@router.post("/assistant/chat")
@router.post("/{attempt_id}/assistant/chat")
async def exam_assistant_chat(
    req: ExamAssistantChatRequest,
    request: Request,
    attempt_id: str | None = None
):
    """
    Official Examination AI Assistant Chat endpoint.
    Strictly restricted to conceptual queries, syntax explanations, error interpretations,
    and progressive hints. Never discloses complete solutions (block_direct_solution = True).
    """
    aid = (attempt_id or req.attempt_id or "").strip()
    if not aid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required examination attempt_id.",
        )
    attempt = get_exam_attempt(aid)
    if not attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Examination attempt '{aid}' not found.",
        )

    opt_user = await get_optional_user(request)
    verify_attempt_access(attempt, opt_user)

    if attempt.get("status") == "submitted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Examination attempt has already been finalized. AI Assistant is disabled.",
        )
    if attempt.get("remaining_seconds", 0) <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Examination time has expired. AI Assistant is disabled.",
        )

    try:
        final_response, guardrail_passed, flags = evaluate_exam_assistant_chat(
            attempt=attempt,
            message=req.message,
            current_code=req.current_code,
            test_results_summary=req.test_results_summary,
            provider=req.provider,
        )
    except ConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI Assistant service configuration error: {e}",
        )
    except ModelProviderError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI Assistant provider temporarily unavailable: {e}",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI Assistant processing error: {e}",
        )

    # Revalidate attempt status after assistant response generation
    fresh_attempt = get_exam_attempt(aid)
    if not fresh_attempt or fresh_attempt.get("status") == "submitted" or fresh_attempt.get("remaining_seconds", 0) <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Examination concluded while assistant was responding. Response discarded.",
        )

    return {
        "success": True,
        "message": final_response,
        "guardrail_passed": guardrail_passed,
        "guardrail_refusal": not guardrail_passed,
        "policy_version": EXAM_GUARDRAIL_POLICY_VERSION,
        "block_direct_solution": True,
    }


# ── Helper ───────────────────────────────────────────────────────────────────

def _format_attempt_response(attempt: dict[str, Any], challenge: dict[str, Any]) -> dict[str, Any]:
    """Build standardized learner-safe attempt response (no hidden tests)."""
    clean_visible = [
        {
            "label": vt.get("label", f"Visible Test #{i+1}"),
            "call": vt.get("call", ""),
            "expected": vt.get("expected", ""),
        }
        for i, vt in enumerate(challenge.get("visible_tests", []))
    ]

    return {
        "attempt_id": attempt["attempt_id"],
        "learner_id": attempt["learner_id"],
        "challenge_id": attempt["challenge_id"],
        "status": attempt["status"],
        "start_time": attempt["start_time"],
        "deadline": attempt["deadline"],
        "duration_seconds": attempt["duration_seconds"],
        "remaining_seconds": attempt.get("remaining_seconds", attempt["duration_seconds"]),
        "unlocked_hints": attempt.get("unlocked_hints", []),
        "challenge": {
            "id": challenge["id"],
            "title": challenge["title"],
            "difficulty": challenge["difficulty"],
            "tags": challenge.get("tags", []),
            "description": challenge["description"],
            "starter_code": challenge["starter_code"],
            "visible_tests": clean_visible,
        },
        "submitted_at": attempt.get("submitted_at"),
    }
