"""Unit briefs and contribution points (M2-07): T49 (deterministic part)."""

from __future__ import annotations

from pathlib import Path

from research_harness.units import brief as brief_mod
from research_harness.workspace.objects import create_object
from research_harness.workspace.workspace import Workspace

_UNIT = "U-ABCDEFGH"


def _object(tmp_path: Path):
    ws = Workspace.init(tmp_path / "Projects")
    return create_object(ws, title="Брифи", kind="article", document_kind="article")


def _brief(points):
    return {
        "unit_id": _UNIT,
        "goal": "Introduce the problem",
        "target_volume": {"min": 1000, "max": 2000},
        "voice": "we",
        "language": "uk",
        "author_points": points,
    }


_P1 = {"id": "AP1", "question": "Яка ваша позиція?", "placeholder_text": "x"}
_P2 = {"id": "AP2", "question": "Який приклад навести?", "placeholder_text": "y"}


def test_two_unanswered_points_two_placeholders(tmp_path: Path) -> None:  # T49
    _oid, folder = _object(tmp_path)
    brief_mod.save_brief(folder, _UNIT, _brief([_P1, _P2]))
    brief, _ = brief_mod.load_brief(folder, _UNIT)
    body = "Intro. {{AP:AP1}} More. {{AP:AP2}}"
    rendered = brief_mod.render_points(brief, body)
    assert rendered.count("[[AUTHOR:") == 2
    assert "[[AUTHOR: Яка ваша позиція?]]" in rendered


def test_answered_point_no_placeholder(tmp_path: Path) -> None:  # T49
    _oid, folder = _object(tmp_path)
    brief_mod.save_brief(folder, _UNIT, _brief([_P1, _P2]))
    brief_mod.answer_point(folder, _UNIT, "AP1", "Моя позиція: X.")
    brief, _ = brief_mod.load_brief(folder, _UNIT)
    body = "Intro. {{AP:AP1}} More. {{AP:AP2}}"
    rendered = brief_mod.render_points(brief, body)
    assert rendered.count("[[AUTHOR:") == 1  # only AP2 remains
    assert "Моя позиція: X." in rendered
    assert (
        brief_mod.unanswered_points(brief) == [_P2] or len(brief_mod.unanswered_points(brief)) == 1
    )


def test_brief_check_required_and_refs(tmp_path: Path) -> None:
    _oid, folder = _object(tmp_path)
    # goal present, target volume missing, an unresolvable excerpt ref
    bad = {"unit_id": _UNIT, "goal": "g", "evidence_refs": ["excerpt:E-99999"]}
    brief_mod.save_brief(folder, _UNIT, bad)
    findings = brief_mod.check_brief(folder, _UNIT)
    ids = {f["check_id"] for f in findings}
    assert "brief.required_missing" in ids  # target volume
    assert "brief.unknown_ref" in ids


def test_brief_check_clean(tmp_path: Path) -> None:
    _oid, folder = _object(tmp_path)
    brief_mod.save_brief(folder, _UNIT, _brief([]))
    findings = brief_mod.check_brief(folder, _UNIT)
    assert not any(f["severity"] in ("blocker", "major") for f in findings)
