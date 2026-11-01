"""Numbers-from-sources check (M3-03, ADR-009 p.4)."""

from __future__ import annotations

from research_harness.review import numbers as n


def test_extract_normalizes_tokens() -> None:
    got = n.extract_numbers("Effect was 42% in 7 cases; ratio 0,45 and 1 234 people.")
    assert "42%" in got and "7" in got and "0.45" in got
    assert "234" in got  # "1 234" splits on the space (no thousands grouping)


def _claim(text: str, ev: list[dict[str, str]], kind: str = "external") -> dict[str, object]:
    return {"id": "C-1", "text": text, "kind": kind, "evidence": ev}


def test_number_missing_from_excerpt_is_flagged() -> None:
    by_id = {"EXC-1": {"id": "EXC-1", "text": "the effect was 42 percentage points"}}
    claim = _claim("The effect was 42%.", [{"type": "excerpt", "id": "EXC-1"}])
    f = n.check_claim_numbers(claim, by_id)
    assert len(f) == 1
    assert f[0]["check_id"] == "review.number_not_in_excerpt" and f[0]["observed"] == "42%"


def test_number_present_in_excerpt_passes() -> None:
    by_id = {"EXC-1": {"id": "EXC-1", "text": "the effect reached 42% overall"}}
    claim = _claim("The effect was 42%.", [{"type": "excerpt", "id": "EXC-1"}])
    assert n.check_claim_numbers(claim, by_id) == []


def test_token_boundary_no_substring_match() -> None:
    by_id = {"EXC-1": {"id": "EXC-1", "text": "17 patients were enrolled"}}
    claim = _claim("We saw 7 cases.", [{"type": "excerpt", "id": "EXC-1"}])
    f = n.check_claim_numbers(claim, by_id)
    assert [x["observed"] for x in f] == ["7"]  # 7 is not matched by 17


def test_no_excerpt_or_no_number_or_internal_is_skipped() -> None:
    assert n.check_claim_numbers(_claim("Has 5 items.", []), {}) == []
    assert (
        n.check_claim_numbers(
            _claim("No digits here.", [{"type": "excerpt", "id": "E"}]),
            {"E": {"id": "E", "text": "x"}},
        )
        == []
    )
    internal = _claim("We argue 5 points.", [{"type": "excerpt", "id": "E"}], kind="internal")
    assert n.check_claim_numbers(internal, {"E": {"id": "E", "text": "x"}}) == []
