"""Entry routing: start and continue (T44, M1 part)."""

from __future__ import annotations

from pathlib import Path

from research_harness.lifecycle import routing
from research_harness.workspace.objects import create_object
from research_harness.workspace.workspace import Workspace


def test_start_in_empty_workspace_creates_and_returns_questions(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "Projects")
    res = routing.start(ws, title="Нова робота", kind="article", lang="uk")
    assert res["result"] == "created"
    assert Path(res["folder"]).is_dir()
    assert res["questions"]  # intake questions returned
    assert any(q["id"] == "Q1" for q in res["questions"])


def test_start_thesis_has_skeleton_units(tmp_path: Path) -> None:
    import yaml

    ws = Workspace.init(tmp_path / "Projects")
    res = routing.start(ws, title="Дисертація", kind="thesis", lang="uk")
    structure = yaml.safe_load((Path(res["folder"]) / "structure.yaml").read_text(encoding="utf-8"))
    kinds = {u["kind"] for u in structure["units"]}
    assert {"introduction", "conclusions", "references"} <= kinds


def test_start_ambiguous_title_returns_candidates(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "Projects")
    create_object(ws, title="Одна назва", kind="article", document_kind="article")
    res = routing.start(ws, title="Одна назва", kind="article", lang="uk")
    assert res["result"] == "ambiguous"
    assert res["candidates"] and res["candidates"][0]["title"] == "Одна назва"


def test_start_revise_mode_unsupported(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "Projects")
    res = routing.start(ws, title="X", kind="article", mode="revise", lang="uk")
    assert res["result"] == "mode_unsupported"


def test_continue_reports_quarantine_without_changing_files(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "Projects")
    _oid, folder = create_object(ws, title="Відновлення", kind="article", document_kind="article")
    quarantine = folder / ".rh" / "quarantine" / "op-synthetic"
    quarantine.mkdir(parents=True)
    (quarantine / "marker").write_text("abandoned\n", encoding="utf-8")

    before = {p.name for p in (folder / ".rh").iterdir()}
    res = routing.continue_object(folder, "uk")
    assert "op-synthetic" in res["status"]["locks_and_recovery"]["quarantined"]
    assert res["next_action"]["command"]
    # No content change: the .rh layout is untouched.
    assert {p.name for p in (folder / ".rh").iterdir()} == before
