"""Rule freshness by date, with an injectable clock (02 §8.4, NFR-12)."""

from __future__ import annotations

from typing import Any

from research_harness.core.clock import default_clock


def today() -> str:
    return default_clock().now_rfc3339()[:10]


def classify(rule: dict[str, Any], at: str | None = None) -> str:
    """Return ``current`` / ``expired`` / ``not_yet_valid`` (ISO dates compare lexically)."""
    now = at or today()
    valid_from = rule.get("valid_from")
    valid_to = rule.get("valid_to")
    review_after = rule.get("review_after")
    if valid_from and now < valid_from:
        return "not_yet_valid"
    if valid_to and now > valid_to:
        return "expired"
    if review_after and now > review_after:
        return "expired"
    return "current"
