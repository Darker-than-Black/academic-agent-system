"""Context packs and budget (M2-09): T52."""

from __future__ import annotations

from pathlib import Path

from research_harness.context import pack as pack_mod
from research_harness.structure import model
from research_harness.summaries import glossary as glossary_mod
from research_harness.summaries import map as map_mod
from research_harness.workspace.objects import create_object
from research_harness.workspace.workspace import Workspace

_UA = "U-AAAAAAAA"
_UB = "U-BBBBBBBB"


def _text(uid: str, body: str) -> str:
    return f"---\nid: {uid}\ntitle: {uid}\nkind: subsection\n---\n{body}\n"


def _object(tmp_path: Path):
    ws = Workspace.init(tmp_path / "Projects")
    _oid, folder = create_object(ws, title="Контекст", kind="thesis", document_kind="thesis")
    model.save(
        folder,
        {
            "schema_version": "0.2",
            "object_id": _oid,
            "labels": {},
            "units": [
                {
                    "id": "CH-1",
                    "kind": "chapter",
                    "title": "Розділ",
                    "children": [
                        {"id": _UA, "kind": "subsection", "title": "A"},
                        {"id": _UB, "kind": "subsection", "title": "B"},
                    ],
                }
            ],
        },
    )
    (folder / "manuscript" / "ch1" / "s1").mkdir(parents=True)
    (folder / "manuscript" / "ch1" / "s2").mkdir(parents=True)
    (folder / "manuscript" / "ch1" / "s1" / "text.md").write_text(
        _text(_UA, "Unit A body."), encoding="utf-8"
    )
    (folder / "manuscript" / "ch1" / "s2" / "text.md").write_text(
        _text(_UB, "Unit B body."), encoding="utf-8"
    )
    (folder / "manuscript" / "ch1" / "s1" / "brief.md").write_text(
        "---\nunit_id: U-AAAAAAAA\ngoal: g\n---\n", encoding="utf-8"
    )
    map_mod.build(folder)
    glossary_mod.add_term(folder, term="t", definition="d", source="author")
    return folder


def test_writer_pack_has_defined_items_and_is_logged(tmp_path: Path) -> None:  # T52
    folder = _object(tmp_path)
    manifest, findings = pack_mod.build_pack(folder, _UA, "writer")
    assert not findings and manifest["within_budget"]
    kinds = {i["kind"] for i in manifest["items"]}
    assert {"brief", "map", "neighbour_summary", "glossary", "chapter_summary"} <= kinds
    assert "unit_text" not in kinds  # writer never gets other units' full text here
    assert (pack_mod.packs_dir(folder) / f"{manifest['id']}.json").is_file()  # logged


def test_over_budget_is_error_listing_items(tmp_path: Path) -> None:  # T52
    folder = _object(tmp_path)
    manifest, findings = pack_mod.build_pack(folder, _UA, "writer", budget=1)
    assert not manifest["within_budget"]
    assert any(f["check_id"] == "context.over_budget" for f in findings)
    assert manifest["items"]  # the error lists the items (no truncation)
    assert not (pack_mod.packs_dir(folder) / f"{manifest['id']}.json").is_file()


def test_orchestrator_refused_full_chapter(tmp_path: Path) -> None:  # T52
    folder = _object(tmp_path)
    manifest, findings = pack_mod.build_pack(folder, "CH-1", "orchestrator")
    assert manifest["refused"] is True
    assert any(f["check_id"] == "context.orchestrator_fulltext" for f in findings)


def test_orchestrator_single_unit_allowed(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    manifest, findings = pack_mod.build_pack(folder, _UA, "orchestrator")
    assert not manifest["refused"] and not findings
