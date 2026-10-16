"""
recommendations.py  —  Debug Dojo Phase 5
=========================================
Personalized next-challenge recommendation engine based on:
  1. Genuine recurring mistakes (mistake category failed across ≥ 2 distinct challenges).
  2. Lowest concept mastery score (prioritizing areas needing growth).
  3. New learner onboarding (beginner-friendly starting challenge).
  4. Flawless learner progression (learners with 0 failures).
  5. Completion celebration when all 10 challenges are mastered.

Guarantees:
  • Never invents a challenge ID; only valid catalogue IDs are recommended.
  • Avoids recommending already-mastered challenges when alternatives exist.
  • Provides a deterministic, evidence-based reason matching learner history.
"""

from typing import Any
from challenges import CHALLENGES, CHALLENGE_BY_ID
from database import (
    ALL_CONCEPTS,
    get_learner_mastery,
    get_recurring_mistakes,
    get_passed_challenges,
    get_learner_progress_counts,
)

# Mapping of mistake taxonomy categories to challenges that heavily test that concept/pattern
MISTAKE_TARGET_CHALLENGES: dict[str, list[str]] = {
    "boundary_comparison": ["count_passes", "sum_positive_numbers", "find_max"],
    "off_by_one": ["first_n_squares", "middle_three", "last_k_total"],
    "unhandled_short_input": ["middle_three", "first_n_squares", "remove_duplicates", "reverse_string"],
    "mutates_input": ["remove_duplicates", "middle_three", "last_k_total"],
    "print_not_return": ["count_passes", "reverse_string", "count_even_numbers", "last_k_total"],
}

# Difficulty ordering for tie-breaking
DIFFICULTY_WEIGHT = {"easy": 1, "medium": 2, "hard": 3}


def get_recommendation(learner_id: str) -> dict[str, Any]:
    """
    Compute the personalized next-challenge recommendation and evidence-based explanation.
    Returns:
      {
        "recommended_challenge": dict | None,
        "recommendation_reason": str,
        "recurring_mistakes": list[str],
        "mastery": dict[str, float],
        "progress_counts": dict[str, int]
      }
    """
    passed_ids = get_passed_challenges(learner_id)
    recurring_mistakes = get_recurring_mistakes(learner_id)
    mastery = get_learner_mastery(learner_id)
    progress = get_learner_progress_counts(learner_id)

    # ── 1. Check if learner has completed all challenges ──────────────
    unpassed_challenges = [
        ch for ch in CHALLENGES
        if ch["id"] not in passed_ids
    ]

    if not unpassed_challenges:
        return {
            "recommended_challenge": None,
            "recommendation_reason": "Congratulations! You have successfully completed all 10 challenges in Debug Dojo.",
            "recurring_mistakes": recurring_mistakes,
            "mastery": mastery,
            "progress_counts": progress,
        }

    # ── 2. Check if learner is brand new (0 submissions) ─────────────
    if progress["total_submissions"] == 0:
        starter_ch = CHALLENGE_BY_ID.get("count_passes") or unpassed_challenges[0]
        return {
            "recommended_challenge": _summarize_challenge(starter_ch),
            "recommendation_reason": "Welcome to Debug Dojo! We recommend starting with 'Count Passes' to practice loops and conditionals.",
            "recurring_mistakes": [],
            "mastery": mastery,
            "progress_counts": progress,
        }

    # ── 3. Prioritize targeting genuine recurring mistakes ────────────
    if recurring_mistakes:
        for rec_cat in recurring_mistakes:
            target_ids = MISTAKE_TARGET_CHALLENGES.get(rec_cat, [])
            # Find an unpassed challenge that targets this recurring mistake
            candidates = [
                CHALLENGE_BY_ID[cid]
                for cid in target_ids
                if cid in CHALLENGE_BY_ID and cid not in passed_ids
            ]
            if candidates:
                # Pick the easiest candidate
                candidates.sort(key=lambda c: DIFFICULTY_WEIGHT.get(c.get("difficulty", "easy"), 2))
                chosen = candidates[0]
                reason = (
                    f"Recommended because you encountered recurring '{rec_cat}' mistakes across multiple challenges. "
                    f"Practicing '{chosen['title']}' will help strengthen your code against this issue."
                )
                return {
                    "recommended_challenge": _summarize_challenge(chosen),
                    "recommendation_reason": reason,
                    "recurring_mistakes": recurring_mistakes,
                    "mastery": mastery,
                    "progress_counts": progress,
                }

    # ── 4. Learners with 0 failures (flawless progress) ───────────────
    if progress["failed_submissions"] == 0:
        # Pick the next unpassed challenge in catalogue order or lowest mastery
        chosen = min(
            unpassed_challenges,
            key=lambda c: min([mastery.get(t, 0.0) for t in c.get("tags", ["lists"])] or [0.0]),
        )
        reason = (
            f"Great work with zero failed submissions so far! Try '{chosen['title']}' "
            f"to continue expanding your Python mastery."
        )
        return {
            "recommended_challenge": _summarize_challenge(chosen),
            "recommendation_reason": reason,
            "recurring_mistakes": recurring_mistakes,
            "mastery": mastery,
            "progress_counts": progress,
        }

    # ── 5. Prioritize concept with lowest mastery score ───────────────
    # Sort concepts by current mastery ascending
    sorted_concepts = sorted(ALL_CONCEPTS, key=lambda c: mastery.get(c, 0.0))

    chosen = None
    target_concept = None
    for concept in sorted_concepts:
        matching_challenges = [
            ch for ch in unpassed_challenges
            if concept in ch.get("tags", [])
        ]
        if matching_challenges:
            matching_challenges.sort(key=lambda c: DIFFICULTY_WEIGHT.get(c.get("difficulty", "easy"), 2))
            chosen = matching_challenges[0]
            target_concept = concept
            break

    if not chosen:
        chosen = unpassed_challenges[0]
        reason = f"Recommended '{chosen['title']}' as your next uncompleted challenge."
    else:
        concept_score = int(round(mastery.get(target_concept, 0.0)))
        reason = (
            f"Recommended to help build your mastery in '{target_concept}' "
            f"(current mastery: {concept_score}%)."
        )

    return {
        "recommended_challenge": _summarize_challenge(chosen),
        "recommendation_reason": reason,
        "recurring_mistakes": recurring_mistakes,
        "mastery": mastery,
        "progress_counts": progress,
    }


def _summarize_challenge(ch: dict[str, Any]) -> dict[str, Any]:
    """Return compact public summary of a challenge."""
    return {
        "id": ch["id"],
        "title": ch["title"],
        "difficulty": ch["difficulty"],
        "tags": ch["tags"],
    }
