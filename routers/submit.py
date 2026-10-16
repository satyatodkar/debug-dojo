"""
routers/submit.py  —  Debug Dojo Phase 3
=========================================
POST /api/submit  —  evaluates learner Python code against visible and hidden tests
using isolated Docker containers.
"""

import asyncio
import uuid
from typing import Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from challenges import CHALLENGE_BY_ID, HIDDEN_TESTS
from sandbox.docker_executor import (
    run_one_test,
    check_docker_available,
    OUTCOME_PASSED,
)
from taxonomy import detect_mistakes
from explanations import generate_explanation
from hint_engine import build_hint_ladder
from storage import save_submission
from database import record_submission, process_submission_progress

router = APIRouter(prefix="/api", tags=["submission"])

MAX_CODE_BYTES = 32 * 1024  # 32 KB limit


class SubmitRequest(BaseModel):
    learner_id: str = Field(..., min_length=1, max_length=100)
    challenge_id: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1)
    hints_requested: int = Field(default=0, ge=0)


@router.post("/submit")
async def submit_code(req: SubmitRequest):
    """
    Validate learner submission, execute tests one by one in Docker containers,
    and return structured test outcomes.
    """
    # ── 1. Validate code size ─────────────────────────────────────────
    code_bytes = len(req.code.encode("utf-8", errors="replace"))
    if code_bytes > MAX_CODE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Submitted code exceeds maximum size limit ({MAX_CODE_BYTES} bytes).",
        )

    # ── 2. Validate challenge ID ──────────────────────────────────────
    cid = req.challenge_id.strip().replace("-", "_")
    challenge = CHALLENGE_BY_ID.get(cid)
    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Challenge '{req.challenge_id}' not found. Check GET /api/challenges for valid IDs.",
        )

    # ── 3. Check Docker sandbox availability (Fail Closed) ───────────
    if not await check_docker_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Code execution sandbox is currently unavailable. Fail closed: code will not be executed on host.",
        )

    fn_name = challenge["id"]
    visible_tests = challenge.get("visible_tests", [])
    hidden_tests = HIDDEN_TESTS.get(cid, [])

    # ── 4. Execute visible tests concurrently (bounded by semaphore) ──
    async def execute_visible(idx: int, vt: dict[str, Any]) -> dict[str, Any]:
        res = await run_one_test(
            learner_code=req.code,
            fn_name=fn_name,
            args=vt.get("args", ()),
            expected=vt.get("expected_val"),
            is_visible=True,
        )
        return {
            "test_id": idx + 1,
            "label": vt.get("label", f"Visible Test #{idx + 1}"),
            "call": vt.get("call", ""),
            "outcome": res.get("outcome"),
            "expected": res.get("expected"),
            "actual": res.get("actual"),
        }

    # ── 5. Execute hidden tests concurrently (bounded by semaphore) ───
    async def execute_hidden(idx: int, ht: dict[str, Any]) -> dict[str, Any]:
        res = await run_one_test(
            learner_code=req.code,
            fn_name=fn_name,
            args=ht.get("args", ()),
            expected=ht.get("expected"),
            is_visible=False,
        )
        # Disclose only test identifier and outcome
        return {
            "test_id": idx + 1,
            "outcome": res.get("outcome"),
        }

    visible_outcomes = await asyncio.gather(
        *(execute_visible(i, vt) for i, vt in enumerate(visible_tests))
    )
    hidden_outcomes = await asyncio.gather(
        *(execute_hidden(i, ht) for i, ht in enumerate(hidden_tests))
    )

    # ── 6. Compute summary ────────────────────────────────────────────
    total_tests = len(visible_outcomes) + len(hidden_outcomes)
    vis_passed = sum(1 for r in visible_outcomes if r["outcome"] == OUTCOME_PASSED)
    hid_passed = sum(1 for r in hidden_outcomes if r["outcome"] == OUTCOME_PASSED)
    total_passed = vis_passed + hid_passed
    all_passed = (total_passed == total_tests)

    if all_passed:
        summary = (
            f"All {total_tests} tests passed "
            f"({vis_passed}/{len(visible_outcomes)} visible, {hid_passed}/{len(hidden_outcomes)} hidden). "
            f"Great job!"
        )
    else:
        summary = (
            f"Passed {total_passed} of {total_tests} tests "
            f"({vis_passed}/{len(visible_outcomes)} visible, {hid_passed}/{len(hidden_outcomes)} hidden). "
            f"Review the visible test details to debug."
        )

    # ── 7. Detect mistakes, generate explanation & build hints ────────
    mistakes = detect_mistakes(req.code, challenge, visible_outcomes, hidden_outcomes)
    explanation = generate_explanation(challenge, visible_outcomes, hidden_outcomes, mistakes, all_passed)
    hint_ladder = build_hint_ladder(challenge, mistakes, visible_outcomes, hidden_outcomes)

    submission_id = f"sub_{uuid.uuid4().hex[:12]}"

    sub_payload = {
        "submission_id": submission_id,
        "learner_id": req.learner_id,
        "challenge_id": challenge["id"],
        "code": req.code,
        "all_passed": all_passed,
        "summary": summary,
        "visible_tests": visible_outcomes,
        "hidden_tests": hidden_outcomes,
        "mistakes": mistakes,
        "explanation": explanation,
        "hint_ladder": hint_ladder,
        "hint_index": req.hints_requested,
    }

    # Save to storage for progressive hints in Phase 4
    save_submission(sub_payload)

    # Save to SQLite database & update concept mastery in Phase 5
    record_submission(sub_payload)
    process_submission_progress(submission_id)

    return {
        "submission_id": submission_id,
        "learner_id": req.learner_id,
        "challenge_id": challenge["id"],
        "all_passed": all_passed,
        "summary": summary,
        "explanation": explanation,
        "mistakes": mistakes,
        "visible_tests": visible_outcomes,
        "hidden_tests": hidden_outcomes,
    }
