"""P2-1: G0 binds to the intake subset, not the whole snapshot (02 §4.2, T09).

A later structure / prose edit leaves intake/answers.json and object.json
untouched, so a valid G0 survives it; G3 (whole-snapshot) does not.
"""

from __future__ import annotations

import json
from pathlib import Path

from research_harness.gates.requests import G0_INTAKE_REFS
from research_harness.state import snapshot as snap
from research_harness.state.freshness import approval_valid
from research_harness.state.store import Store
from research_harness.structure import model
from research_harness.units.write import write_body
from research_harness.workspace.objects import create_object
from research_harness.workspace.workspace import Workspace

_U = "U-AAAAAAAA"
_P = "PG-AAAAAA"


def _object(tmp_path: Path) -> Path:
    ws = Workspace.init(tmp_path / "Projects")
    _oid, folder = create_object(ws, title="Зв'язок", kind="article", document_kind="article")
    (folder / "intake" / "answers.json").write_text(
        json.dumps({"answers": {"Q1": {"value": "x"}}}, ensure_ascii=False), encoding="utf-8"
    )
    model.save(
        folder,
        {
            "schema_version": "0.2",
            "object_id": _oid,
            "labels": {},
            "units": [{"id": _U, "kind": "section", "title": "Р"}],
        },
    )
    d = folder / "manuscript" / "01"
    d.mkdir(parents=True)
    (d / "text.md").write_text(f"---\nid: {_U}\ntitle: Р\nkind: section\n---\n", "utf-8")
    write_body(folder, _U, f"<!-- {_P} -->\nПерше речення.\n", by="author")
    return folder


def _target(folder: Path, refs: list[str]) -> dict:
    cur = snap.read_current(folder)
    return {
        "target": {
            "snapshot_id": cur,
            "manifest_sha256": snap.load_snapshot(folder, cur)["manifest_sha256"],
            "refs": refs,
        }
    }


def test_g0_survives_structure_edit_but_g3_does_not(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    Store(folder).checkpoint(by="human", note="intake complete")

    g0 = _target(folder, list(G0_INTAKE_REFS))
    g3 = _target(folder, [])  # whole-snapshot binding
    assert approval_valid(folder, g0) is True
    assert approval_valid(folder, g3) is True

    # A2-style edit: change the manuscript body (structure/prose), not intake.
    write_body(folder, _U, f"<!-- {_P} -->\nПерше речення. Додано друге.\n", by="author")
    Store(folder).checkpoint(by="human", note="A2 edit")

    assert approval_valid(folder, g0) is True  # intake answers + object.json unchanged
    assert approval_valid(folder, g3) is False  # whole snapshot changed


def test_g0_invalidated_when_intake_answer_changes(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    Store(folder).checkpoint(by="human", note="intake complete")
    g0 = _target(folder, list(G0_INTAKE_REFS))
    assert approval_valid(folder, g0) is True

    (folder / "intake" / "answers.json").write_text(
        json.dumps({"answers": {"Q1": {"value": "CHANGED"}}}, ensure_ascii=False), encoding="utf-8"
    )
    Store(folder).checkpoint(by="human", note="intake edited")
    assert approval_valid(folder, g0) is False  # a bound intake file changed
