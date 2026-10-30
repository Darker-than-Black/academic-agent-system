"""Status report across the F5b lifecycle states (T29a, M1 part)."""

from __future__ import annotations

from pathlib import Path

from research_harness.lifecycle import status as status_mod
from research_harness.workspace.workspace import Workspace
from research_harness_dev.fixtures.f5b import build_f5b_lifecycle


def _reports(tmp_path: Path) -> dict[str, dict]:
    build_f5b_lifecycle(tmp_path)
    ws = Workspace.find(tmp_path / "Projects")
    out = {}
    for o in ws.list_objects():
        rep = status_mod.build_report(ws.object_folder(o["id"]), "uk")
        out[rep["stage"]["current"]] = rep
    return out


def test_current_stage_matches_each_state(tmp_path: Path) -> None:
    reports = _reports(tmp_path)
    assert set(reports) == {"A0", "A2", "A12", "A14", "A16"}
    assert reports["A16"]["stage"]["states"]["A16"] == "waiting"


def test_exactly_one_next_action_and_required_fields(tmp_path: Path) -> None:
    for rep in _reports(tmp_path).values():
        na = rep["next_action"]
        assert na["who"] in ("agent", "author")
        assert na["command"]
        for key in (
            "object",
            "stage",
            "gates",
            "blockers",
            "unknowns",
            "dirty",
            "stale",
            "locks_and_recovery",
        ):
            assert key in rep


def test_a0_object_blocks_on_intake(tmp_path: Path) -> None:
    rep = _reports(tmp_path)["A0"]
    assert any(b.get("reason") == "intake.required_missing" for b in rep["blockers"])
    assert rep["next_action"]["who"] == "agent"
    assert "intake questions" in rep["next_action"]["command"]


def test_a12_object_has_open_g3_request(tmp_path: Path) -> None:
    rep = _reports(tmp_path)["A12"]
    g3 = next(g for g in rep["gates"] if g["gate"] == "G3")
    assert g3["request_open"] is True
    assert g3["approval_valid"] is False
