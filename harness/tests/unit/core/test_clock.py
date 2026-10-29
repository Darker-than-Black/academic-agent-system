"""Clock tests (02 §1.5): injectable only in test mode."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from research_harness.core import clock


def test_default_clock_is_utc() -> None:
    now = clock.Clock().now()
    assert now.tzinfo is not None
    assert now.utcoffset() == UTC.utcoffset(None)


def test_rfc3339_format() -> None:
    c = clock.Clock()
    text = c.now_rfc3339()
    assert text.endswith("Z")
    assert len(text) == 20  # YYYY-MM-DDTHH:MM:SSZ


def test_override_requires_test_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RH_TEST_MODE", raising=False)
    with pytest.raises(PermissionError):
        clock.Clock(datetime(2026, 10, 29))


def test_override_in_test_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RH_TEST_MODE", "1")
    c = clock.Clock(datetime(2026, 10, 29, tzinfo=UTC))
    assert c.today().isoformat() == "2026-10-29"


def test_parse_clock_override() -> None:
    assert clock.parse_clock_override("2026-10-29").date().isoformat() == "2026-10-29"
    assert clock.parse_clock_override("2026-10-29T12:00:00Z").hour == 12
