"""`review fulltext` resolves cite keys against bib_keys, not source ids.

Regression: run() built the valid-key set from source ids (S-0001), while cite
markers carry the bib_key ([[cite:meng2024]]), so every real citation was
falsely flagged as missing from the bibliography — a verified-export blocker.
"""

from __future__ import annotations

from pathlib import Path

from research_harness.review import fulltext as ft
from research_harness.sources import registry
from research_harness.structure import model
from research_harness.units.write import write_body
from research_harness.workspace.objects import create_object
from research_harness.workspace.workspace import Workspace

_U = "U-AAAAAAAA"
_P = "PG-AAAAAA"


def _object(tmp_path: Path) -> Path:
    ws = Workspace.init(tmp_path / "Projects")
    oid, folder = create_object(ws, title="Цитати", kind="article", document_kind="article")
    registry.add_records(
        folder,
        [{"title": "Meng 2024", "bib_key": "meng2024", "metadata_status": "matched"}],
    )
    model.save(
        folder,
        {
            "schema_version": "0.2",
            "object_id": oid,
            "labels": {},
            "units": [{"id": _U, "kind": "section", "title": "Р"}],
        },
    )
    d = folder / "manuscript" / "01"
    d.mkdir(parents=True)
    (d / "text.md").write_text(f"---\nid: {_U}\ntitle: Р\nkind: section\n---\n", "utf-8")
    return folder, oid


def test_cite_key_matching_bibkey_is_not_flagged(tmp_path: Path) -> None:
    folder, _oid = _object(tmp_path)
    write_body(folder, _U, f"<!-- {_P} -->\nЯк показано [[cite:meng2024]].\n", by="author")
    cite_findings = [f for f in ft.run(folder) if f["check_id"] == "fulltext.cite_keys"]
    assert cite_findings == []


def test_unknown_cite_key_is_still_blocked(tmp_path: Path) -> None:
    folder, _oid = _object(tmp_path)
    write_body(folder, _U, f"<!-- {_P} -->\nЗа [[cite:ghost2099]].\n", by="author")
    cite_findings = [f for f in ft.run(folder) if f["check_id"] == "fulltext.cite_keys"]
    assert len(cite_findings) == 1
    assert cite_findings[0]["severity"] == "blocker"
    assert cite_findings[0]["observed"] == "ghost2099"


def test_source_id_is_not_a_valid_cite_key(tmp_path: Path) -> None:
    # Citing the internal id instead of the bib_key must be flagged.
    folder, _oid = _object(tmp_path)
    write_body(folder, _U, f"<!-- {_P} -->\nЗа [[cite:S-0001]].\n", by="author")
    cite_findings = [f for f in ft.run(folder) if f["check_id"] == "fulltext.cite_keys"]
    assert any(f["observed"] == "S-0001" for f in cite_findings)
