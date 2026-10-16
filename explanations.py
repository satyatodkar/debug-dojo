"""
explanations.py  —  Debug Dojo Phase 4
======================================
Generates plain-language failure explanations based on test outcomes,
challenge requirements, and confirmed mistake tags.

Safety guarantees:
  - Never reveals hidden test inputs, expected values, or student outputs on hidden tests.
  - Never reveals internal exception tracebacks.
  - Distinguishes confirmed findings from possible causes.
  - Does NOT give away complete solutions.
"""

from typing import Any


def generate_explanation(
    challenge: dict[str, Any],
    visible_results: list[dict[str, Any]],
    hidden_results: list[dict[str, Any]],
    mistakes: list[dict[str, str]],
    all_passed: bool,
) -> str:
    """
    Construct a clear, plain-language explanation of test results.
    """
    if all_passed:
        return (
            "All test cases passed successfully! Your function correctly satisfies "
            "all requirements and handles edge cases."
        )

    parts: list[str] = []

    # 1. Observed behavioral findings (Confirmed)
    vis_wrong = [r for r in visible_results if r.get("outcome") == "wrong output"]
    vis_err   = [r for r in visible_results if r.get("outcome") == "runtime error"]
    vis_time  = [r for r in visible_results if r.get("outcome") == "timeout"]
    vis_pass  = [r for r in visible_results if r.get("outcome") == "passed"]

    hid_total = len(hidden_results)
    hid_pass  = sum(1 for r in hidden_results if r.get("outcome") == "passed")

    findings = []
    if vis_err:
        findings.append("Encountered a runtime error on visible test cases.")
    if vis_time:
        findings.append("Execution timed out (likely due to an infinite or prolonged loop).")
    if vis_wrong:
        findings.append(f"Produced incorrect return values on {len(vis_wrong)} visible test case(s).")
    if vis_pass and not vis_wrong and not vis_err and not vis_time and hid_pass < hid_total:
        findings.append("All visible tests passed, but some hidden edge cases failed.")

    if findings:
        parts.append(f"Confirmed observation: {' '.join(findings)}")

    # 2. Possible causes & Guidance (Evidence-based)
    causes: list[str] = []
    for m in mistakes:
        cat = m.get("category")
        evidence = m.get("evidence")
        if cat == "boundary_comparison":
            causes.append(
                f"Boundary comparison issue: {evidence} "
                "Check whether your condition should use '>=' rather than '>' (or '<=' vs '<') "
                "so values right on the threshold are handled correctly."
            )
        elif cat == "print_not_return":
            causes.append(
                f"Missing return value: {evidence} "
                "Functions must return their answer using the 'return' keyword so the caller can use the result."
            )
        elif cat == "unhandled_short_input":
            causes.append(
                f"Edge case handling: {evidence} "
                "Consider adding a check for short or empty inputs before performing indexing or slicing."
            )
        elif cat == "off_by_one":
            causes.append(
                f"Index or range offset: {evidence} "
                "Double-check your loop range and slice boundaries to ensure you cover all intended items."
            )
        elif cat == "mutates_input":
            causes.append(
                f"In-place mutation: {evidence} "
                "Avoid modifying the argument list directly. Build a fresh collection and return that instead."
            )

    if causes:
        parts.append("Possible cause: " + " ".join(causes))
    else:
        # General guidance when no specific pattern was definitively identified
        if vis_err:
            parts.append(
                "Possible cause: Check for invalid operations such as division by zero, "
                "accessing an index that does not exist, or referencing an undefined variable."
            )
        elif vis_time:
            parts.append(
                "Possible cause: A while loop condition may never become False, "
                "or a loop counter is not advancing on every iteration."
            )
        else:
            parts.append(
                "Possible cause: The logic may not cover all input scenarios specified in the challenge description. "
                "Trace your code step-by-step with the first failing test case."
            )

    # 3. Safe aggregate hidden test note
    if hid_total > 0:
        parts.append(
            f"Hidden tests status: {hid_pass} of {hid_total} passed. "
            "(Hidden test inputs and expected values are kept confidential to promote genuine debugging.)"
        )

    return " \n\n".join(parts)
