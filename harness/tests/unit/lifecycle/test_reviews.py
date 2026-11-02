"""Reviewer comments (M3-08, FR-41, T44)."""

from __future__ import annotations

from pathlib import Path

import pytest

from research_harness.core.errors import InvalidInputError
from research_harness.lifecycle import reviews as rv


def test_add_respond_cycle(tmp_path: Path) -> None:
    c = rv.add_comment(
        tmp_path, round=1, reviewer="R2", text="Clarify sampling.", location_hint="§3.2"
    )
    assert c["id"] == "RC-01" and c["status"] == "open"
    assert rv.open_count(tmp_path) == 1

    closed = rv.respond(
        tmp_path, "RC-01", action="accept", response="Done in §3.2.", changed_units=["U-ABCDEFGH"]
    )
    assert closed["status"] == "closed" and closed["action"] == "accept"
    assert closed["changed_units"] == ["U-ABCDEFGH"]
    assert rv.open_count(tmp_path) == 0


def test_second_comment_increments(tmp_path: Path) -> None:
    rv.add_comment(tmp_path, round=1, reviewer="R1", text="a")
    c2 = rv.add_comment(tmp_path, round=2, reviewer="R2", text="b")
    assert c2["id"] == "RC-02"
    assert len(rv.list_comments(tmp_path)) == 2


def test_respond_unknown_comment(tmp_path: Path) -> None:
    with pytest.raises(InvalidInputError):
        rv.respond(tmp_path, "RC-99", action="accept", response="x")
