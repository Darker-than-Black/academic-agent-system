"""ULID generator tests (02 §1.2)."""

from __future__ import annotations

from research_harness.core import ulid


def test_ulid_length_and_charset() -> None:
    value = ulid.new_ulid()
    assert len(value) == 26
    assert ulid.is_ulid(value)


def test_ulid_monotonic_same_millisecond() -> None:
    fixed = 1_700_000_000_000
    values = [ulid.new_ulid(now_ms=fixed) for _ in range(50)]
    assert values == sorted(values)  # lexicographic order preserved
    assert len(set(values)) == len(values)  # all distinct


def test_ulid_time_ordering_across_ms() -> None:
    earlier = ulid.new_ulid(now_ms=1_700_000_000_000)
    later = ulid.new_ulid(now_ms=1_700_000_001_000)
    assert earlier < later


def test_is_ulid_rejects_bad() -> None:
    assert not ulid.is_ulid("short")
    assert not ulid.is_ulid("I" * 26)  # I not in Crockford alphabet
