"""ID allocator and validator tests (02 §1.2)."""

from __future__ import annotations

import pytest

from research_harness.core import ids


def test_object_id_format_and_widening() -> None:
    assert ids.object_id("article", 2026, 1) == "A-2026-001"
    assert ids.object_id("thesis", 2026, 12) == "T-2026-012"
    assert ids.object_id("article", 2026, 1000) == "A-2026-1000"  # widens past 999
    assert ids.is_valid("article", "A-2026-1000")


def test_counter_ids() -> None:
    assert ids.counter_id("material", 7) == "M-0007"
    assert ids.counter_id("excerpt", 31) == "E-00031"
    assert ids.counter_id("definition", 3) == "DEF-003"
    assert ids.counter_id("submission", 4) == "SUB-04"
    assert ids.counter_id("excerpt", 100000) == "E-100000"  # widens past width


def test_result_row_id() -> None:
    assert ids.result_row_id(1, 2) == "RR-0001-0002"
    assert ids.is_valid("result_row", "RR-0001-0002")


def test_claim_v01_pattern_still_valid() -> None:
    assert ids.is_valid("claim", "C-5")
    assert ids.is_valid("claim", "C-0012")


def test_unit_id_random_valid_and_unique() -> None:
    seen: set[str] = set()
    for _ in range(200):
        uid = ids.new_unit_id(seen)
        assert ids.is_valid("unit", uid)
        assert uid not in seen
        seen.add(uid)


def test_unit_id_collision_retry() -> None:
    # Pre-seed every value the generator could produce once, except by retry.
    uid = ids.new_unit_id(set())
    again = ids.new_unit_id({uid})
    assert again != uid


def test_ulid_based_ids_valid() -> None:
    assert ids.is_valid("workspace", ids.new_workspace_id())
    assert ids.is_valid("operation", ids.new_operation_id())
    assert ids.is_valid("snapshot", ids.new_snapshot_id())
    assert ids.is_valid("event", ids.new_event_id())
    assert ids.is_valid("model_call", ids.new_model_call_id())
    assert ids.is_valid("handoff", ids.new_handoff_id())


def test_invalid_ids_rejected() -> None:
    assert not ids.is_valid("unit", "U-ILOU0000")  # excluded Crockford letters
    assert not ids.is_valid("article", "A-26-1")
    assert not ids.is_valid("excerpt", "E-0001")  # too few digits
    with pytest.raises(ValueError):
        ids.validate("material", "M-1")
    with pytest.raises(KeyError):
        ids.is_valid("nonsense", "x")


def test_counter_id_rejects_nonpositive() -> None:
    with pytest.raises(ValueError):
        ids.counter_id("material", 0)
