"""
taxonomy.py  —  Debug Dojo Phase 4
==================================
Mistake category detection based on AST inspection and behavioral test outcomes.

Required categories (exact names):
  1. off_by_one
  2. unhandled_short_input
  3. print_not_return
  4. boundary_comparison
  5. mutates_input

Rules:
  - Each category has its own understandable detection method.
  - Do NOT label a mistake merely because a pattern appears; validate that
    both static structure and test outcomes support the category.
  - Returns a list of dicts: {"category": str, "evidence": str, "confidence": str}.
  - Returns [] when there is insufficient evidence.
"""

import ast
from typing import Any

CATEGORY_OFF_BY_ONE            = "off_by_one"
CATEGORY_UNHANDLED_SHORT_INPUT = "unhandled_short_input"
CATEGORY_PRINT_NOT_RETURN      = "print_not_return"
CATEGORY_BOUNDARY_COMPARISON   = "boundary_comparison"
CATEGORY_MUTATES_INPUT         = "mutates_input"


def detect_mistakes(
    code: str,
    challenge: dict[str, Any],
    visible_results: list[dict[str, Any]],
    hidden_results: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """
    Evaluate student code and test outcomes against the five mistake categories.
    Returns only categories where evidence supports the classification.
    """
    mistakes: list[dict[str, str]] = []

    # Parse AST safely; if syntax is invalid, static checks are skipped
    tree = None
    try:
        tree = ast.parse(code)
    except SyntaxError:
        pass

    # 1. print_not_return
    m = _check_print_not_return(tree, visible_results, hidden_results)
    if m:
        mistakes.append(m)

    # 2. boundary_comparison
    m = _check_boundary_comparison(tree, challenge, visible_results, hidden_results)
    if m:
        mistakes.append(m)

    # 3. unhandled_short_input
    m = _check_unhandled_short_input(challenge, visible_results, hidden_results)
    if m:
        mistakes.append(m)

    # 4. off_by_one
    m = _check_off_by_one(tree, challenge, visible_results, hidden_results)
    if m:
        mistakes.append(m)

    # 5. mutates_input
    m = _check_mutates_input(tree, challenge, visible_results, hidden_results)
    if m:
        mistakes.append(m)

    return mistakes


# ---------------------------------------------------------------------------
# 1. print_not_return
# ---------------------------------------------------------------------------
def _check_print_not_return(
    tree: ast.AST | None,
    visible_results: list[dict[str, Any]],
    hidden_results: list[dict[str, Any]],
) -> dict[str, str] | None:
    """
    Detects if the function outputs via print() rather than returning a value,
    confirmed by the function returning None when a non-None value is expected.
    """
    # Check if actual output on failed visible tests was "None" or "(error: ...None...)"
    none_returned = False
    for r in visible_results:
        if r.get("outcome") in ("wrong output", "runtime error"):
            actual = str(r.get("actual", ""))
            expected = str(r.get("expected", ""))
            if "None" in actual and "None" not in expected:
                none_returned = True
                break

    if not none_returned:
        return None

    # Check AST for print() usage and missing return statements
    has_print = False
    has_meaningful_return = False

    if tree:
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "print":
                    has_print = True
            elif isinstance(node, ast.Return):
                if node.value is not None:
                    has_meaningful_return = True

    if has_print and not has_meaningful_return:
        return {
            "category": CATEGORY_PRINT_NOT_RETURN,
            "evidence": "Function printed output instead of returning it; tests received None.",
            "confidence": "high",
        }
    elif has_print and none_returned:
        return {
            "category": CATEGORY_PRINT_NOT_RETURN,
            "evidence": "Code calls print() and returned None on test cases expecting a computed value.",
            "confidence": "medium",
        }

    return None


# ---------------------------------------------------------------------------
# 2. boundary_comparison
# ---------------------------------------------------------------------------
def _check_boundary_comparison(
    tree: ast.AST | None,
    challenge: dict[str, Any],
    visible_results: list[dict[str, Any]],
    hidden_results: list[dict[str, Any]],
) -> dict[str, str] | None:
    """
    Detects boundary condition errors where strict inequalities (> or <)
    were used instead of non-strict (>= or <=), or vice versa.
    """
    cid = challenge.get("id", "")

    # Specific known boundary challenges:
    # count_passes: boundary is 40 (must be >= 40)
    # sum_positive_numbers: boundary is 0 (must be > 0, strictly positive)
    if cid == "count_passes":
        # Look for '>' comparison with 40 or variable
        has_strict_gt_40 = False
        if tree:
            for node in ast.walk(tree):
                if isinstance(node, ast.Compare):
                    for op, comparator in zip(node.ops, node.comparators):
                        if isinstance(op, ast.Gt):
                            if isinstance(comparator, ast.Constant) and comparator.value == 40:
                                has_strict_gt_40 = True

        # Check if visible test #1 (which has 40) failed with outcome 'wrong output'
        v1 = visible_results[0] if visible_results else {}
        if v1.get("outcome") == "wrong output" and has_strict_gt_40:
            return {
                "category": CATEGORY_BOUNDARY_COMPARISON,
                "evidence": "Condition uses '>' instead of '>=' with threshold 40, excluding exact passing marks.",
                "confidence": "high",
            }
        return None

    elif cid == "sum_positive_numbers":
        has_ge_zero = False
        if tree:
            for node in ast.walk(tree):
                if isinstance(node, ast.Compare):
                    for op, comparator in zip(node.ops, node.comparators):
                        if isinstance(op, ast.GtE):
                            if isinstance(comparator, ast.Constant) and comparator.value == 0:
                                has_ge_zero = True
        v1 = visible_results[0] if visible_results else {}
        if v1.get("outcome") == "wrong output" and has_ge_zero:
            return {
                "category": CATEGORY_BOUNDARY_COMPARISON,
                "evidence": "Condition uses '>=' with 0 instead of strict '>', treating zero as positive.",
                "confidence": "high",
            }

    return None


# ---------------------------------------------------------------------------
# 3. unhandled_short_input
# ---------------------------------------------------------------------------
def _check_unhandled_short_input(
    challenge: dict[str, Any],
    visible_results: list[dict[str, Any]],
    hidden_results: list[dict[str, Any]],
) -> dict[str, str] | None:
    """
    Detects when code fails on short, single-element, or empty inputs
    while longer inputs succeed.
    """
    cid = challenge.get("id", "")

    # For first_n_squares, test #3 is n = 0
    if cid == "first_n_squares":
        if len(visible_results) >= 3:
            v3 = visible_results[2]
            v1_pass = visible_results[0].get("outcome") == "passed"
            if v3.get("outcome") in ("wrong output", "runtime error") and v1_pass:
                return {
                    "category": CATEGORY_UNHANDLED_SHORT_INPUT,
                    "evidence": "Failed on edge case n = 0 while normal positive n inputs passed.",
                    "confidence": "high",
                }

    # For middle_three, test #3 is short list [7, 8]
    if cid == "middle_three":
        if len(visible_results) >= 3:
            v3 = visible_results[2]
            v1_pass = visible_results[0].get("outcome") == "passed"
            if v3.get("outcome") in ("wrong output", "runtime error") and v1_pass:
                return {
                    "category": CATEGORY_UNHANDLED_SHORT_INPUT,
                    "evidence": "Failed when list length is fewer than three elements while 5-element list passed.",
                    "confidence": "high",
                }

    # For remove_duplicates, test #3 is empty list []
    if cid == "remove_duplicates":
        if len(visible_results) >= 3:
            v3 = visible_results[2]
            v1_pass = visible_results[0].get("outcome") == "passed"
            if v3.get("outcome") in ("wrong output", "runtime error") and v1_pass:
                return {
                    "category": CATEGORY_UNHANDLED_SHORT_INPUT,
                    "evidence": "Failed on empty list [] input while non-empty inputs passed.",
                    "confidence": "high",
                }

    return None


# ---------------------------------------------------------------------------
# 4. off_by_one
# ---------------------------------------------------------------------------
def _check_off_by_one(
    tree: ast.AST | None,
    challenge: dict[str, Any],
    visible_results: list[dict[str, Any]],
    hidden_results: list[dict[str, Any]],
) -> dict[str, str] | None:
    """
    Detects loop range or slice boundary off-by-one errors.
    """
    cid = challenge.get("id", "")

    if cid == "first_n_squares":
        # Starter code has range(n) which starts from 0 instead of 1, ending at n-1
        has_range_n = False
        if tree:
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id == "range":
                        if len(node.args) == 1:
                            has_range_n = True

        v1 = visible_results[0] if visible_results else {}
        if v1.get("outcome") == "wrong output" and has_range_n:
            return {
                "category": CATEGORY_OFF_BY_ONE,
                "evidence": "Loop range starts at 0 instead of 1 (e.g. range(n) produces 0..n-1 instead of 1..n).",
                "confidence": "high",
            }

    elif cid == "middle_three":
        # Slice mid - 1 : mid + 1 produces length 2 instead of 3
        has_short_slice = False
        if tree:
            for node in ast.walk(tree):
                if isinstance(node, ast.Slice):
                    # check if slice upper - lower == 2
                    has_short_slice = True

        v1 = visible_results[0] if visible_results else {}
        if v1.get("outcome") == "wrong output":
            actual = str(v1.get("actual", ""))
            expected = str(v1.get("expected", ""))
            if len(actual.split(",")) != len(expected.split(",")):
                return {
                    "category": CATEGORY_OFF_BY_ONE,
                    "evidence": "Slice returned an incorrect number of elements (middle three requires 3 elements).",
                    "confidence": "high",
                }

    return None


# ---------------------------------------------------------------------------
# 5. mutates_input
# ---------------------------------------------------------------------------
def _check_mutates_input(
    tree: ast.AST | None,
    challenge: dict[str, Any],
    visible_results: list[dict[str, Any]],
    hidden_results: list[dict[str, Any]],
) -> dict[str, str] | None:
    """
    Detects in-place mutation of input arguments (such as .pop(), .sort(),
    or 'del' operations on arguments).
    """
    if not tree:
        return None

    # Get function parameter names
    param_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for arg in node.args.args:
                param_names.add(arg.arg)

    mutating_methods = {"pop", "sort", "reverse", "clear", "remove", "extend"}
    found_mutation = None

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr in mutating_methods:
                    if isinstance(node.func.value, ast.Name) and node.func.value.id in param_names:
                        found_mutation = node.func.attr
                        break
        elif isinstance(node, ast.Delete):
            for target in node.targets:
                if isinstance(target, ast.Subscript):
                    if isinstance(target.value, ast.Name) and target.value.id in param_names:
                        found_mutation = "del"
                        break

    if found_mutation:
        # Check if there are failures
        has_failure = any(r.get("outcome") != "passed" for r in visible_results + hidden_results)
        if has_failure:
            return {
                "category": CATEGORY_MUTATES_INPUT,
                "evidence": f"Code modifies input parameter in-place using .{found_mutation}(), which alters the caller's data.",
                "confidence": "high",
            }

    return None
