"""Methods auto-inject (M4-17 render): {{methodology}} marker in export."""

from __future__ import annotations

from pathlib import Path

from research_harness.export_docx import assemble, methods_inject
from research_harness.methodology import record as methodology
from research_harness.sources import registry
from research_harness.structure import model
from research_harness.workspace.objects import create_object
from research_harness.workspace.workspace import Workspace

_U = "U-AAAAAAAA"

_RECORD = {
    "schema_version": "0.2",
    "selection_criteria": {"inclusion": ["peer-reviewed"], "exclusion": ["no data"]},
    "search_log": {"counts": {"found": 142, "screened": 40, "included": 9, "excluded": 31}},
}


def _object(tmp_path: Path, body: str):
    ws = Workspace.init(tmp_path / "Projects")
    oid, folder = create_object(ws, title="Методи", kind="article", document_kind="article")
    model.save(
        folder,
        {
            "schema_version": "0.2",
            "object_id": oid,
            "labels": {},
            "units": [{"id": _U, "kind": "section", "title": "Матеріали і методи"}],
        },
    )
    (folder / "manuscript" / "a").mkdir(parents=True)
    (folder / "manuscript" / "a" / "text.md").write_text(
        f"---\nid: {_U}\ntitle: Матеріали і методи\nkind: section\n---\n{body}", encoding="utf-8"
    )
    return folder


def test_marker_renders_methodology_block(tmp_path: Path) -> None:
    folder = _object(tmp_path, "Опис методів. {{methodology}}")
    methodology.save(folder, dict(_RECORD))
    registry.add_records(
        folder,
        [{"author": "Smith, J.", "title": "A", "year": "2020", "metadata_status": "matched"}],
    )
    md = assemble.assemble_markdown(folder)
    assert "{{methodology}}" not in md
    assert "## Критерії відбору" in md
    assert "## Включені джерела" in md


def test_marker_present_but_nothing_to_render_is_gap(tmp_path: Path) -> None:
    folder = _object(tmp_path, "Методи. {{methodology}}")  # no record, no sources
    g = methods_inject.gaps(folder, ["Методи. {{methodology}}"])
    assert any(f["check_id"] == "methodology.marker_empty" for f in g)


def test_record_without_marker_is_unplaced_gap(tmp_path: Path) -> None:
    folder = _object(tmp_path, "Методи без маркера.")
    methodology.save(folder, dict(_RECORD))
    g = methods_inject.gaps(folder, ["Методи без маркера."])
    assert any(f["check_id"] == "methodology.unplaced" for f in g)


def test_no_marker_no_record_no_gap(tmp_path: Path) -> None:
    folder = _object(tmp_path, "Звичайний текст методів.")
    assert methods_inject.gaps(folder, ["Звичайний текст методів."]) == []
