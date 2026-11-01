"""Document-wide fulltext checks (M3-04, FR-49)."""

from __future__ import annotations

from research_harness.review import fulltext as ft


def test_crossref_unresolved_is_blocker() -> None:
    bodies = {"U-AAAAAAAA": "See {{ref:U-BBBBBBBB}}.", "U-CCCCCCCC": "body"}
    f = ft.check_crossref(bodies)
    assert len(f) == 1
    assert f[0]["check_id"] == "fulltext.crossref" and f[0]["severity"] == "blocker"
    assert f[0]["observed"] == "U-BBBBBBBB"


def test_crossref_resolved_passes() -> None:
    bodies = {"U-AAAAAAAA": "See {{ref:U-CCCCCCCC}}.", "U-CCCCCCCC": "body"}
    assert ft.check_crossref(bodies) == []


def test_cite_key_unknown_is_blocker() -> None:
    bodies = {"U-AAAAAAAA": "Per @S-0001 and @S-9999 it holds."}
    f = ft.check_cite_keys(bodies, {"S-0001"})
    assert [x["observed"] for x in f] == ["S-9999"]
    assert f[0]["check_id"] == "fulltext.cite_keys" and f[0]["severity"] == "blocker"


def test_cite_key_bracket_syntax() -> None:
    bodies = {"U-AAAAAAAA": "As shown [[cite:S-0002]]."}
    assert ft.check_cite_keys(bodies, {"S-0002"}) == []
    assert ft.check_cite_keys(bodies, set())[0]["observed"] == "S-0002"


def _words(n: int) -> str:
    return " ".join(f"w{i}" for i in range(n))


def test_repeated_fragment_across_units() -> None:
    shared = _words(45)
    bodies = {"U-AAAAAAAA": f"intro {shared} end", "U-BBBBBBBB": f"other {shared} tail"}
    f = ft.check_repeated_fragment(bodies)
    assert len(f) >= 1
    assert f[0]["check_id"] == "fulltext.repeated_fragment" and f[0]["severity"] == "major"


def test_short_overlap_not_flagged() -> None:
    shared = _words(20)  # below the 40-word threshold
    bodies = {"U-AAAAAAAA": shared, "U-BBBBBBBB": shared}
    assert ft.check_repeated_fragment(bodies) == []


def test_same_unit_repeat_not_cross_unit() -> None:
    shared = _words(45)
    bodies = {"U-AAAAAAAA": f"{shared} .... {shared}"}
    assert ft.check_repeated_fragment(bodies) == []
