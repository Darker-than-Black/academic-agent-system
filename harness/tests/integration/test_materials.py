"""Materials manifest: hashes, duplicate linking, malformed DOI, private (T38)."""

from __future__ import annotations

from pathlib import Path

from research_harness.materials import manifest
from research_harness.workspace.objects import create_object
from research_harness.workspace.workspace import Workspace
from research_harness_dev.fixtures.f4w_metadata import build_f4w_metadata


def _object(tmp_path: Path):
    ws = Workspace.init(tmp_path / "Projects")
    return create_object(ws, title="Матеріали", kind="article", document_kind="article")


def test_bibtex_duplicate_and_malformed_doi(tmp_path: Path) -> None:
    _oid, folder = _object(tmp_path)
    src = build_f4w_metadata(tmp_path / "f4w") / "refs.bib"
    entry, findings = manifest.add_bibtex(folder, src)

    assert entry["sha256"]
    records = {r["bib_key"]: r for r in entry["records"]}
    # Preprint linked to the published version (linked, not merged).
    assert records["shevchenko2024preprint"]["duplicate_of"] == "shevchenko2024"
    assert "shevchenko2024preprint" in records and "shevchenko2024" in records  # both kept
    # Malformed DOI flagged and left unresolved.
    assert any(f["check_id"] == "materials.doi_malformed" for f in findings)
    assert records["broken2024"]["metadata_status"] == "unresolved"
    assert any(f["check_id"] == "materials.duplicate_linked" for f in findings)


def test_private_pdf_not_in_git_tree(tmp_path: Path) -> None:
    _oid, folder = _object(tmp_path)
    pdf = tmp_path / "foreign.pdf"
    pdf.write_bytes(b"%PDF-1.7 synthetic\n")
    entry = manifest.add_file(folder, pdf, kind="file", private=True)
    assert entry["path"].startswith("materials/private/")
    assert entry["permissions"]["private"] is True
    # stored=false for materials/private (blob not kept in the snapshot store).
    from research_harness.state.snapshot import STORED_FALSE_PREFIXES

    assert any(entry["path"].startswith(p) for p in STORED_FALSE_PREFIXES)


def test_docx_manuscript_hashed(tmp_path: Path) -> None:
    _oid, folder = _object(tmp_path)
    docx = tmp_path / "draft.docx"
    docx.write_bytes(b"PK\x03\x04 synthetic docx\n")
    entry = manifest.add_file(folder, docx, kind="manuscript")
    assert entry["kind"] == "manuscript" and entry["sha256"]
    assert manifest.load(folder)["materials"][-1]["id"] == entry["id"]
