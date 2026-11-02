"""DOCX import: tracked changes and comments map to units, nothing is lost,
provenance follows the change author (M3-09; docx.md; T46, T58)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from research_harness.import_docx import apply
from research_harness.intake.answers import load as load_answers
from research_harness.provenance import paragraphs as prov
from research_harness.structure import model
from research_harness.units.write import read_body, write_body
from research_harness.workspace.objects import create_object
from research_harness.workspace.workspace import Workspace
from research_harness_dev.fixtures.f5d_docx import build_f5d_docx

_UNIT = "U-MPRT2345"
_P1 = "PG-MP2345"
_P2 = "PG-MP2346"


def _object(tmp_path: Path) -> Path:
    ws = Workspace.init(tmp_path / "Projects")
    _oid, folder = create_object(ws, title="Ревізія", kind="article", document_kind="article")
    model.save(
        folder,
        {
            "schema_version": "0.2",
            "object_id": _oid,
            "labels": {},
            "units": [{"id": _UNIT, "kind": "section", "title": "Розділ"}],
        },
    )
    unit_dir = folder / "manuscript" / "01 Розділ"
    unit_dir.mkdir(parents=True)
    (unit_dir / "text.md").write_text(
        f"---\nid: {_UNIT}\ntitle: Розділ\nkind: section\n---\n",
        encoding="utf-8",
    )
    # Agent-written body: both paragraphs start with origin ``agent`` so a human
    # edit on import must become ``agent_edited_by_author`` (FR-53).
    body = f"<!-- {_P1} -->\nТекст один.\n\n<!-- {_P2} -->\nТекст два. зайве\n"
    write_body(folder, _UNIT, body, by="agent")
    return folder


def test_clean_import_maps_everything(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    docx = tmp_path / "reviewed.docx"
    build_f5d_docx(docx, unit_id=_UNIT, para_ids=(_P1, _P2))

    result = apply.import_docx(folder, docx, source="editor")

    assert result["blocked"] is False
    assert result["count"] == 3  # one ins, one del, one comment
    assert result["mapped"] == 3 and result["unmapped"] == 0
    assert result["units"] == [_UNIT]

    imp = Path(result["dir"])
    assert (imp / "original.docx").is_file()
    assert (imp / "changes.json").is_file()
    assert (imp / "plan.json").is_file()
    assert (imp / "diff.md").is_file()
    assert not (imp / "unmapped.json").exists()

    # Count invariant (T46): in == mapped + unmapped, recorded and valid.
    record = json.loads((imp / "changes.json").read_text(encoding="utf-8"))
    assert record["count"] == record["mapped"] + record["unmapped"]

    # Entered revise mode scoped to the touched unit.
    assert load_answers(folder)["mode"] == "revise"


def test_proposed_origin_and_diff(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    docx = tmp_path / "reviewed.docx"
    build_f5d_docx(docx, unit_id=_UNIT, para_ids=(_P1, _P2))

    result = apply.import_docx(folder, docx)
    plan = json.loads((Path(result["dir"]) / "plan.json").read_text(encoding="utf-8"))
    diffs = {d["paragraph_id"]: d for u in plan["units"] for d in u["diffs"]}

    assert _P1 in diffs  # insertion changes the text
    assert diffs[_P1]["proposed_origin"] == "agent_edited_by_author"
    assert diffs[_P1]["accepted_text"] == "Текст один. додано"


def test_accepting_import_updates_provenance(tmp_path: Path) -> None:
    """The author accepting a mapped change (write by author) sets the origin to
    ``agent_edited_by_author`` — the real provenance update (FR-53)."""
    folder = _object(tmp_path)
    assert prov.load_map(folder, _UNIT)[_P1]["origin"] == "agent"

    new_body = f"<!-- {_P1} -->\nТекст один. додано\n\n<!-- {_P2} -->\nТекст два.\n"
    write_body(folder, _UNIT, new_body, by="author")

    pmap = prov.load_map(folder, _UNIT)
    assert pmap[_P1]["origin"] == "agent_edited_by_author"
    assert "Текст один. додано" in read_body(folder, _UNIT)


def test_unmapped_change_blocks_and_is_kept(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    docx = tmp_path / "reviewed.docx"
    build_f5d_docx(docx, unit_id=_UNIT, para_ids=(_P1, _P2), with_unmapped=True)

    result = apply.import_docx(folder, docx)

    assert result["blocked"] is True
    assert result["unmapped"] == 1 and result["count"] == 4
    assert any(f["check_id"] == "import.unmapped_changes" for f in result["findings"])
    unmapped = json.loads((Path(result["dir"]) / "unmapped.json").read_text(encoding="utf-8"))
    assert len(unmapped) == 1 and unmapped[0]["unit_id"] is None


def test_non_docx_is_refused(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    bad = tmp_path / "notes.txt"
    bad.write_text("plain", encoding="utf-8")
    from research_harness.core.errors import BlockedError

    with pytest.raises(BlockedError):
        apply.import_docx(folder, bad)
