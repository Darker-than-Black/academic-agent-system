"""Import sources from files, manual exports and DOI lists into the registry.

The raw export file is copied to ``sources/inbox/`` (gitignored); a normalized
record of it with its hash is written to ``sources/exports/<hash>.json`` (in
git, foreign-text-free). Each import appends a line to ``sources/import-log.jsonl``
as a STUB for the M2-03 search log (``rh search log``), which supersedes it when
M2-03 merges (noted in the PR).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from research_harness.core.clock import default_clock
from research_harness.core.hashing import file_hash
from research_harness.sources import registry
from research_harness.sources.import_exports import parse_export
from research_harness.state.snapshot import atomic_write_bytes


def _inbox(root: Path) -> Path:
    d = root / "sources" / "inbox"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _exports_dir(root: Path) -> Path:
    d = root / "sources" / "exports"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _log_import(root: Path, entry: dict[str, Any]) -> None:
    """STUB search-log line (superseded by rh search log in M2-03)."""
    path = root / "sources" / "import-log.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _store_export(root: Path, src: Path, parsed: list[dict[str, Any]], fmt: str) -> str:
    """Copy the raw export to inbox (gitignored); write its normalized record."""
    dest = _inbox(root) / src.name
    shutil.copy2(src, dest)
    export_hash = file_hash(dest)
    record = {
        "schema_version": "0.2",
        "export_sha256": export_hash,
        "original_name": src.name,
        "format": fmt,
        "imported_at": default_clock().now_rfc3339(),
        "record_count": len(parsed),
    }
    atomic_write_bytes(
        _exports_dir(root) / f"{export_hash}.json",
        (json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    )
    return export_hash


def import_export(
    root: Path, src: Path, from_source: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Import a manual export (scopus/wos/scholar/zotero/ris/bibtex/csv)."""
    text = src.read_text(encoding="utf-8", errors="replace")
    parsed, fmt = parse_export(from_source, text)
    export_hash = _store_export(root, src, parsed, fmt)
    now = default_clock().now_rfc3339()
    meta = [{"resource": f"import:{from_source}", "record_id": export_hash, "retrieved_at": now}]
    added, findings = registry.add_records(root, parsed, metadata_sources=meta)
    _log_import(
        root,
        {
            "at": now,
            "kind": "import",
            "from_source": from_source,
            "format": fmt,
            "count": len(added),
            "export_sha256": export_hash,
            "file": src.name,
        },
    )
    return added, findings


def import_doi_list(
    root: Path, dois: list[str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Register sources from a list of DOIs (identity first; no lookup yet)."""
    parsed = [{"bib_key": f"doi{i + 1}", "doi": d} for i, d in enumerate(dois) if d.strip()]
    now = default_clock().now_rfc3339()
    added, findings = registry.add_records(root, parsed)
    _log_import(
        root,
        {"at": now, "kind": "import", "from_source": "doi", "count": len(added)},
    )
    return added, findings


def add_fulltext(
    root: Path,
    source_id: str,
    src: Path,
    *,
    version: str = "unknown",
    obtained_via: str = "author",
    license_: str | None = None,
) -> dict[str, Any]:
    """Register an author-provided legal full text for a source (gitignored copy)."""
    from research_harness.sources import registry

    source = registry.get(root, source_id)
    if source is None:
        raise KeyError(source_id)
    fulltext_dir = root / "sources" / "fulltext"
    fulltext_dir.mkdir(parents=True, exist_ok=True)
    ext = src.suffix or ".pdf"
    dest = fulltext_dir / f"{source_id}{ext}"
    shutil.copy2(src, dest)
    fulltext: dict[str, Any] = {
        "local_path": dest.relative_to(root).as_posix(),
        "sha256": file_hash(dest),
        "version": version if version in ("published", "accepted", "preprint") else "unknown",
        "obtained_via": obtained_via,
    }
    if license_:
        fulltext["license"] = license_
    source["fulltext"] = fulltext
    source["access_level"] = "local_original"
    return registry.update(root, source_id, source)


def import_file(
    root: Path, src: Path, *, kind: str = "file"
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Register a non-bibliographic file (e.g. a PDF) as one source with provenance.

    The file lands in ``sources/inbox/`` (gitignored); a minimal metadata-only
    source record is created with ``metadata_status: unresolved`` for later
    ``rh source lookup``.
    """
    dest = _inbox(root) / src.name
    shutil.copy2(src, dest)
    fhash = file_hash(dest)
    now = default_clock().now_rfc3339()
    parsed = [{"bib_key": src.stem, "title": src.name, "type": kind}]
    meta = [{"resource": "import:file", "record_id": fhash, "retrieved_at": now}]
    added, findings = registry.add_records(root, parsed, metadata_sources=meta)
    _log_import(root, {"at": now, "kind": "import", "from_source": "file", "file": src.name})
    return added, findings
