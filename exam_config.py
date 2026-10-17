"""
exam_config.py — Debug Dojo Examination Configuration
======================================================
Central configuration for examination mode:
  • Difficulty-based timers (Easy: 15m, Medium: 25m, Hard: 40m)
  • Authoritative deadlines
  • Resource and sandbox limits
  • Integrity event thresholds
"""

import os

# ── Timer Configurations (in seconds) ─────────────────────────────────────────
# Default durations strictly based on challenge difficulty metadata
DIFFICULTY_DURATIONS: dict[str, int] = {
    "easy": 15 * 60,    # 15 minutes (900 seconds)
    "medium": 25 * 60,  # 25 minutes (1500 seconds)
    "hard": 40 * 60,    # 40 minutes (2400 seconds)
}

# Configurable short timer for testing / development without waiting 15+ minutes
# Enabled if DEBUG_DOJO_DEV_TIMER is set or via dev override parameter
DEV_TEST_TIMER_SECONDS: int = int(os.environ.get("DEBUG_DOJO_DEV_TIMER", "15"))

# Warning thresholds (seconds remaining)
WARNING_THRESHOLD_5M: int = 5 * 60   # 300 seconds
WARNING_THRESHOLD_1M: int = 1 * 60   # 60 seconds

# ── Examination Sandbox Resource Limits ───────────────────────────────────────
EXAM_TIMEOUT_PER_TEST: float = 10.0   # 10.0s wall-clock limit per individual test (generous margin for macOS Docker VM)
EXAM_MEMORY_LIMIT: str = "128m"       # 128 MiB container memory cap
EXAM_MAX_OUTPUT_BYTES: int = 65536    # 64 KiB maximum combined captured output
EXAM_MAX_CODE_BYTES: int = 32 * 1024  # 32 KiB submission source limit

# ── Integrity Policy Configuration ───────────────────────────────────────────
INTEGRITY_WARNING_THRESHOLD: int = 3   # Show warning banner after N integrity events
INTEGRITY_RATE_LIMIT_PER_MIN: int = 60 # Maximum integrity events accepted per minute per attempt
