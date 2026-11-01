"""Budget controller and cost guard (models-budget.md; M3-01, FR-13, NFR-05).

Reimplemented clean-room from the module contract (no third-party code copied;
the AutoResearchClaw #22 ``cost_guard.py`` pattern is a reference only, so no
adoption record is triggered — H4). The core stays LLM-free (H5).
"""

from __future__ import annotations

from research_harness.budget.controller import (
    DEFAULT_THRESHOLDS,
    LIMIT_KEYS,
    UNKNOWN,
    budget_path,
    check,
    evaluate,
    load_budget,
    usage_from_calls,
)

__all__ = [
    "DEFAULT_THRESHOLDS",
    "LIMIT_KEYS",
    "UNKNOWN",
    "budget_path",
    "check",
    "evaluate",
    "load_budget",
    "usage_from_calls",
]
