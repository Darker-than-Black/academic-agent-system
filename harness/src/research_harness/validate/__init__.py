"""Validation framework and checks (02 §9.4, 03 §2).

`rh validate --scope …` runs registered checks (read-only). M1-03 ships the
framework plus two check families: ``schema`` (records against their JSON
Schema) and ``refs`` (every ref resolves to a known artifact). Later cards
register freshness (M1-05) and structure (M1-07) checks against the same
framework.
"""

from __future__ import annotations

from research_harness.validate.framework import (
    Check,
    Finding,
    ValidationContext,
    finding,
    has_blocker,
    registry,
    run_checks,
)

__all__ = [
    "Check",
    "Finding",
    "ValidationContext",
    "finding",
    "has_blocker",
    "registry",
    "run_checks",
]
