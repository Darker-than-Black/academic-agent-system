"""Injectable clock (02 §1.5): UTC everywhere in records.

``--clock`` / an injected override is honoured only when ``RH_TEST_MODE=1`` so
rule-freshness tests can pin "today"; in normal runs it is ignored.
"""

from __future__ import annotations

import os
from datetime import UTC, date, datetime


def test_mode() -> bool:
    return os.environ.get("RH_TEST_MODE") == "1"


class Clock:
    """Source of the current UTC time; overridable only in test mode."""

    def __init__(self, override: datetime | None = None) -> None:
        if override is not None and not test_mode():
            raise PermissionError("clock override is only allowed when RH_TEST_MODE=1")
        if override is not None and override.tzinfo is None:
            override = override.replace(tzinfo=UTC)
        self._override = override

    def now(self) -> datetime:
        """Current UTC time (timezone-aware)."""
        if self._override is not None:
            return self._override.astimezone(UTC)
        return datetime.now(UTC)

    def today(self) -> date:
        """Current UTC date."""
        return self.now().date()

    def now_rfc3339(self) -> str:
        """Current UTC time as RFC 3339 with ``Z``, second precision."""
        return self.now().strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_clock_override(value: str) -> datetime:
    """Parse a ``--clock`` ISO date/datetime into an aware UTC datetime."""
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        parsed = datetime.combine(date.fromisoformat(value), datetime.min.time())
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


_default = Clock()


def default_clock() -> Clock:
    return _default
