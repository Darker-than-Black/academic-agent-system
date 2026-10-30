"""Draft export: order, anchors stripped, references, gaps, manifest hashes,
bookmarks, no fabricated sources (M2-12; T46/T11/T43 deterministic part)."""

from __future__ import annotations

import json
from pathlib import Path

from research_harness.claims import ledger as ledger_mod
from research_harness.core.hashing import file_hash
from research_harness.export_docx import assemble, references
from research_harness.sources import registry
from research_harness.structure import model
from research_harness.workspace.objects import create_object
from research_harness.workspace.workspace import Workspace

_U1 = "U-AAAAAAAA"
_U2 = "U-BBBBBBBB"


def _object(tmp_path: Path):
    ws = Workspace.init(tmp_path / "Projects")
    oid, folder = create_object(ws, title="Експорт", kind="article", document_kind="article")
    model.save(
        folder,
        {
            "schema_version": "0.2",
            "object_id": oid,
            "labels": {},
            "units": [
                {"id": _U1, "kind": "section", "title": "Перший"},
                {"id": _U2, "kind": "section", "title": "Другий"},
            ],
        },
    )
    (folder / "manuscript" / "a").mkdir(parents=True)
    (folder / "manuscript" / "b").mkdir(parents=True)
    (folder / "manuscript" / "a" / "text.md").write_text(
        f"---\nid: {_U1}\ntitle: Перший\nkind: section\n---\n"
        "<!-- PG-ABC123 -->\nWe cite @koval2019 here. [[AUTHOR: fill this]]\n",
        encoding="utf-8",
    )
    (folder / "manuscript" / "b" / "text.md").write_text(
        f"---\nid: {_U2}\ntitle: Другий\nkind: section\n---\n"
        "<!-- PG-DEF456 -->\nAnd @smith2020 and the missing @ghost9999.\n",
        encoding="utf-8",
    )
    return oid, folder


def _sources(folder: Path) -> None:
    registry.add_records(
        folder,
        [
            {
                "bib_key": "koval2019",
                "author": "Коваль, І. І.",
                "title": "Про щось",
                "container": "Вісник",
                "year": "2019",
                "metadata_status": "matched",
            },
            {
                "bib_key": "smith2020",
                "author": "Smith, J.",
                "title": "On things",
                "container": "Journal",
                "year": "2020",
                "metadata_status": "matched",
            },
        ],
    )


def test_assemble_order_and_anchors_stripped(tmp_path: Path) -> None:  # T46
    _oid, folder = _object(tmp_path)
    md = assemble.assemble_markdown(folder)
    assert md.index("# Перший") < md.index("# Другий")  # structure order
    assert "PG-ABC123" not in md and "<!--" not in md  # anchors stripped
    assert "[[AUTHOR: fill this]]" in md  # placeholder visible


def test_references_exclude_unresolved_and_sort(tmp_path: Path) -> None:  # T43, H6
    _oid, folder = _object(tmp_path)
    _sources(folder)
    bib, gaps = references.build(folder)
    assert "koval2019" in bib and "smith2020" in bib  # resolved cited keys
    assert "ghost9999" not in bib  # never fabricated
    assert any(g["check_id"] == "export.cite_unresolved" for g in gaps)
    # Romanized sort: Koval (Koval) before Smith.
    assert bib.index("koval2019") < bib.index("smith2020")


def test_export_draft_md_manifest_and_gaps(tmp_path: Path) -> None:  # T11
    _oid, folder = _object(tmp_path)
    _sources(folder)
    ledger_mod.set_claims(
        folder,
        _U1,
        [
            {
                "text": "weak claim",
                "kind": "external",
                "materiality": "material",
                "evidence": [],
                "support": "unreviewed",
            }
        ],
    )
    result = assemble.export_draft(folder, fmt="md")
    outdir = Path(result["dir"])

    assert result["format"] == "md"
    ids = {g["check_id"] for g in result["gaps"]}
    assert {"export.cite_unresolved", "export.placeholder", "export.claim_unsupported"} <= ids

    manifest = json.loads((outdir / "manifest.json").read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        assert file_hash(outdir / entry["path"]) == entry["sha256"]  # hashes match files
    # Bookmarks for every unit and every paragraph anchor.
    assert manifest["bookmarks"][_U1] == f"unit_{_U1}"
    assert manifest["bookmarks"]["PG-ABC123"] == "para_PG-ABC123"
    assert manifest["bookmarks"]["PG-DEF456"] == "para_PG-DEF456"
