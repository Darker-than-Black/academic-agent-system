"""OOXML tracked-change parsing (M3-09, parse.py)."""

from __future__ import annotations

from pathlib import Path

from research_harness.import_docx.parse import parse_docx
from research_harness_dev.fixtures.f5d_docx import build_f5d_docx


def test_parse_changes_and_accepted(tmp_path: Path) -> None:
    docx = build_f5d_docx(tmp_path / "r.docx", with_unmapped=True)
    parsed = parse_docx(docx)

    kinds = sorted(c.type for c in parsed.changes)
    assert kinds == ["comment", "del", "ins", "ins"]
    # Raw count (ins/del/move elements) + comments == assembled changes (T46).
    assert parsed.count == len(parsed.changes) == 4

    ins = next(c for c in parsed.changes if c.type == "ins" and c.unit_id)
    assert ins.author == "Editor" and ins.text == "додано"
    assert ins.unit_id == "U-MPRT2345" and ins.paragraph_id == "PG-MP2345"

    comment = next(c for c in parsed.changes if c.type == "comment")
    assert comment.author == "Supervisor" and comment.text == "уточніть джерело"

    # Insertions kept, deletions dropped in the accepted text.
    assert parsed.accepted["PG-MP2345"] == "Текст один. додано"
    assert parsed.accepted["PG-MP2346"] == "Текст два."
