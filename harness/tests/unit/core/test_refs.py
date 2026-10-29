"""Artifact reference parsing / formatting tests (02 §1.4)."""

from __future__ import annotations

import pytest

from research_harness.core.refs import Ref, parse_ref

CASES = [
    ("unit:U-7K2M9QXA/text", Ref("unit", "U-7K2M9QXA", "text", None)),
    ("source:S-0012", Ref("source", "S-0012", None, None)),
    ("rulepack:ua-mon-phd@2026-10-27", Ref("rulepack", "ua-mon-phd", None, "2026-10-27")),
    ("author:profile@v3", Ref("author", "profile", None, "v3")),
    ("object:A-2026-001/structure", Ref("object", "A-2026-001", "structure", None)),
    ("file:materials/inbox/notes.txt", Ref("file", "materials/inbox/notes.txt", None, None)),
]


@pytest.mark.parametrize("text,expected", CASES)
def test_parse(text: str, expected: Ref) -> None:
    assert parse_ref(text) == expected


@pytest.mark.parametrize("text,_expected", CASES)
def test_round_trip(text: str, _expected: Ref) -> None:
    assert parse_ref(text).format() == text


@pytest.mark.parametrize("bad", ["", "nokind", "unit:", ":id", "file:../escape"])
def test_invalid_refs(bad: str) -> None:
    with pytest.raises(ValueError):
        parse_ref(bad)
