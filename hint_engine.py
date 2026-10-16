"""
hint_engine.py  —  Debug Dojo Phase 4
=====================================
Generates a 3-step progressive hint ladder for any failure:
  - Hint 1: Poses a useful question.
  - Hint 2: Directs attention to the relevant concept or behavior.
  - Hint 3: Narrows down the suspected issue without supplying the full fix.

Safety rules:
  - Never reveals complete solutions.
  - Never reveals hidden test inputs or expected answers.
  - Returns deterministic, pedagogical hints.
"""

from typing import Any

# Challenge-specific default ladders when no specific category is tagged
CHALLENGE_DEFAULT_LADDERS: dict[str, list[str]] = {
    "last_k_total": [
        "Are you taking elements from the beginning of the list, or from the end of the list?",
        "In Python, negative slice indices like `[-k:]` select elements from the end of a list.",
        "Check how you slice `marks`: slicing from the back `marks[-k:]` ensures you sum the last `k` marks.",
    ],
    "count_passes": [
        "What exact score qualifies as a pass according to the requirements: is 40 a pass or a fail?",
        "Look closely at the comparison operator: in Python, `>` excludes 40, while `>=` includes 40.",
        "Check the `if` statement inside your loop: ensure marks equal to 40 are counted as passing.",
    ],
    "first_n_squares": [
        "What is the first integer whose square should be in the list: 0 or 1?",
        "In Python, `range(n)` starts at 0 and stops before `n`. To start at 1, use `range(1, n + 1)`.",
        "Update your loop range to begin at 1 and end at `n + 1` so that 1 through n are squared.",
    ],
    "middle_three": [
        "How many elements should be in the returned list, and what should happen if the input is short?",
        "Check the slice length: if `mid` is the center index, taking `[mid - 1 : mid + 2]` yields exactly 3 items.",
        "Verify your slice upper bound: in Python slice notation `[start:stop]`, the element at `stop` is excluded.",
    ],
    "count_even_numbers": [
        "What mathematical property defines an even integer in Python?",
        "The modulo operator `%` calculates the remainder. An even integer divided by 2 has a remainder of 0 (`n % 2 == 0`).",
        "Check whether your condition checks `n % 2 == 0` (even) instead of `n % 2 == 1` (odd).",
    ],
    "find_max": [
        "What happens if all numbers in the list are negative, like `[-5, -1, -8]`?",
        "Initializing your `largest` variable to 0 causes issues if every number in the list is negative.",
        "Consider initializing `largest` to the very first item in the list (`numbers[0]`) instead of 0.",
    ],
    "reverse_string": [
        "As you loop through each character, are you adding it to the front or the back of your accumulator?",
        "To reverse a string by iterating, each new character should be placed in front of the accumulated result.",
        "Change `result = result + ch` to `result = ch + result` so characters are prepended.",
    ],
    "count_vowels": [
        "Does your function count uppercase vowels like 'A' or 'E' as vowels?",
        "Python string comparison is case-sensitive. 'A' is not in 'aeiou'.",
        "Convert the character or input string to lowercase using `.lower()` before checking if it is in vowels.",
    ],
    "sum_positive_numbers": [
        "Is the number zero considered strictly positive in mathematics?",
        "A positive number is strictly greater than zero (`> 0`). Zero itself is neither positive nor negative.",
        "Ensure your condition checks `n > 0` rather than `n >= 0` so zero is excluded from the sum.",
    ],
    "remove_duplicates": [
        "Are you adding unique items to your return list as you discover them?",
        "Check your accumulator: when an item is not yet in `seen`, it should also be appended to `result`.",
        "Inside the `if item not in seen:` block, make sure you append the item to your return list.",
    ],
}


def build_hint_ladder(
    challenge: dict[str, Any],
    mistakes: list[dict[str, str]],
    visible_results: list[dict[str, Any]],
    hidden_results: list[dict[str, Any]],
) -> list[str]:
    """
    Build a 3-step progressive hint ladder based on the detected mistake category,
    falling back to tailored challenge hints or failure-type hints.
    """
    cid = challenge.get("id", "")

    # 1. Category-specific hint ladders
    for m in mistakes:
        cat = m.get("category")
        if cat == "boundary_comparison":
            return [
                "What does the problem specification state about the exact passing threshold: is a score of 40 a pass or a fail?",
                "In Python, the `>` operator only matches numbers strictly greater than 40. Look closely at the comparison operator inside your loop.",
                "Check the `if` statement inside your loop: ensure marks equal to 40 are counted by checking if mark is greater than or equal to 40.",
            ]
        elif cat == "print_not_return":
            return [
                "What does your function give back to the caller when it finishes executing?",
                "In Python, `print()` displays characters on screen, but callers and test runners only receive values returned with `return`.",
                "Ensure your function has an explicit `return <value>` statement at the end instead of only calling print().",
            ]
        elif cat == "unhandled_short_input":
            return [
                "What should your function return when given an empty list or a list with fewer elements than expected?",
                "Think about edge cases: accessing indices on short collections can lead to unexpected errors if not handled first.",
                "Add an early guard condition at the start of your function to handle short or empty inputs before slicing or indexing.",
            ]
        elif cat == "off_by_one":
            return [
                "How many elements does your function return, and how does that compare to what the test case expects?",
                "Remember that Python slice notation `[start:stop]` excludes the element at index `stop`, and `range(n)` stops before `n`.",
                "Check the start and stop indices in your loop or slice: verify whether you need to adjust by +1.",
            ]
        elif cat == "mutates_input":
            return [
                "Is your code modifying the list that was passed in, or is it building a fresh output list?",
                "Methods like `.pop()`, `.sort()`, or `del` modify objects in-place, which can break caller assumptions.",
                "Create a new list `result = []` and append to it instead of removing from or altering the input parameter.",
            ]

    # 2. Failure-type specific ladders
    has_timeout = any(r.get("outcome") == "timeout" for r in visible_results + hidden_results)
    if has_timeout:
        return [
            "Why might a loop continue running indefinitely without reaching a stopping condition?",
            "Check your loop conditions and variables: is the loop counter advancing on every single iteration?",
            "Ensure your loop has a clear termination condition that is guaranteed to be reached for any input.",
        ]

    has_runtime_error = any(r.get("outcome") == "runtime error" for r in visible_results + hidden_results)
    if has_runtime_error:
        return [
            "What kind of error occurred during execution (e.g. invalid syntax, division by zero, or missing variable)?",
            "Review the operations in your function: ensure all referenced variables are defined and inputs match expected types.",
            "Trace the first test input through your code by hand line by line to verify every operation is valid.",
        ]

    # 3. Challenge-specific tailored fallback
    if cid in CHALLENGE_DEFAULT_LADDERS:
        return CHALLENGE_DEFAULT_LADDERS[cid]

    # 4. Ultimate fallback
    return [
        "What specific requirement from the challenge description is the failing test checking?",
        "Compare the expected output with your function's actual output for the first visible test case.",
        "Walk through your function step-by-step with the input to identify where the logic diverges from the specification.",
    ]
