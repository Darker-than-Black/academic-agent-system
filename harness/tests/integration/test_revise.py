"""Revise mode and its docx entry point (M3-08/M3-09, lifecycle-records.md)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from research_harness.cli import lifecycle_ops
from research_harness.intake.answers import load as load_answers
from research_harness.lifecycle import revise as revise_mod
from research_harness.structure import model
from research_harness.units.write import write_body
from research_harness.workspace.objects import create_object
from research_harness.workspace.workspace import Workspace
from research_harness_dev.fixtures.f5d_docx import build_f5d_docx

_U1 = "U-MPRT2345"
_U2 = "U-MPRT2346"
_P1 = "PG-MP2345"
_P2 = "PG-MP2346"


def _object(tmp_path: Path) -> Path:
    ws = Workspace.init(tmp_path / "Projects")
    _oid, folder = create_object(ws, title="Rev", kind="article", document_kind="article")
    model.save(
        folder,
        {
            "schema_version": "0.2",
            "object_id": _oid,
            "labels": {},
            "units": [
                {"id": _U1, "kind": "section", "title": "Один"},
                {"id": _U2, "kind": "section", "title": "Два"},
            ],
        },
    )
    for n, uid in ((1, _U1), (2, _U2)):
        d = folder / "manuscript" / f"0{n}"
        d.mkdir(parents=True)
        (d / "text.md").write_text(f"---\nid: {uid}\ntitle: t\nkind: section\n---\n", "utf-8")
    write_body(
        folder,
        _U1,
        f"<!-- {_P1} -->\nТекст один.\n\n<!-- {_P2} -->\nТекст два. зайве\n",
        by="agent",
    )
    return folder


def test_enter_revise_proposes_locks_outside_scope(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    report = revise_mod.enter_revise(folder, [_U1])
    assert report["scope"] == [_U1]
    assert report["propose_lock"] == [_U2]
    assert load_answers(folder)["mode"] == "revise"


def test_revise_from_docx_routes_through_import(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    docx = tmp_path / "reviewed.docx"
    build_f5d_docx(docx, unit_id=_U1, para_ids=(_P1, _P2))

    args = SimpleNamespace(command="revise", root=str(folder), from_file=str(docx), scope=None)
    envelope, code = lifecycle_ops.route(args, "en")

    assert code == 0 and envelope["status"] == "ok"
    assert envelope["command"] == "import"  # delegated to the docx importer
    assert load_answers(folder)["mode"] == "revise"
    assert (folder / "history" / "imports").is_dir()
