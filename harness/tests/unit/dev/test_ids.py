"""PH-1: dev unit/paragraph ID helper mints and validates (Crockford base32)."""

from __future__ import annotations

import re

import pytest

from research_harness.core.ids import PATTERNS
from research_harness_dev import ids


def test_patterns_reflect_crockford_exclusions() -> None:
    # The excluded letters must never be accepted in a suffix.
    for bad in ("I", "L", "O", "U"):
        assert not ids.is_valid_unit_id("U-" + bad * 8)
        assert not ids.is_valid_paragraph_id("PG-" + bad * 6)


def test_unit_id_constructor_validates() -> None:
    assert ids.unit_id("00000001") == "U-00000001"
    assert PATTERNS["unit"].match(ids.unit_id("ABCD2345"))
    for bad in ("0000001", "000000001", "0000000I", "0000000l", "0000000o"):
        with pytest.raises(ValueError):
            ids.unit_id(bad)


def test_paragraph_id_constructor_validates() -> None:
    assert ids.paragraph_id("MP2345") == "PG-MP2345"
    assert PATTERNS["paragraph"].match(ids.paragraph_id("ABC234"))
    for bad in ("MP234", "MP23456", "MP234I", "mp234o"):
        with pytest.raises(ValueError):
            ids.paragraph_id(bad)


def test_mint_is_deterministic_and_valid() -> None:
    assert ids.mint_unit_id(1) == ids.mint_unit_id(1)
    assert ids.mint_paragraph_id(1) == ids.mint_paragraph_id(1)
    assert ids.mint_unit_id(0) == "U-00000000"
    # index 32 -> second Crockford digit rolls over (…10)
    assert ids.mint_unit_id(32) == "U-00000010"
    for i in (0, 1, 31, 32, 1000, 32**6 - 1):
        assert PATTERNS["unit"].match(ids.mint_unit_id(i))
    for i in (0, 1, 31, 32, 1000):
        assert PATTERNS["paragraph"].match(ids.mint_paragraph_id(i))


def test_mint_rejects_overflow_and_negative() -> None:
    with pytest.raises(ValueError):
        ids.mint_paragraph_id(-1)
    with pytest.raises(ValueError):
        ids.mint_paragraph_id(32**6)  # one too wide for 6 chars


def test_minted_ids_never_contain_excluded_letters() -> None:
    excluded = re.compile(r"[ILOU]")
    for i in range(0, 2000, 7):
        assert not excluded.search(ids.mint_unit_id(i)[2:])
        assert not excluded.search(ids.mint_paragraph_id(i)[3:])
