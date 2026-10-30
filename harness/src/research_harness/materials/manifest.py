"""Materials manifest: register files, bib/RIS/DOI lists, link duplicates (02 §9.2)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from research_harness.core.clock import default_clock
from research_harness.core.hashing import file_hash
from research_harness.materials.bib import parse_bibtex
from research_harness.materials.dedup import link_duplicates
from research_harness.materials.doi_list import is_valid_doi, normalize_doi, parse_doi_list
from research_harness.materials.ris import parse_ris
from research_harness.state.snapshot import atomic_write_bytes


def manifest_path(root: Path) -> Path:
    return root / "materials" / "manifest.json"


def load(root: Path) -> dict[str, Any]:
    p = manifest_path(root)
    if p.is_file():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"schema_version": "0.2", "materials": []}


def save(root: Path, data: dict[str, Any]) -> None:
    atomic_write_bytes(
        manifest_path(root), (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )


def _next_id(data: dict[str, Any]) -> str:
    return f"M-{len(data['materials']) + 1:04d}"


def _permissions(private: bool, external_api: str = "unknown") -> dict[str, Any]:
    return {
        "external_api": external_api,
        "personal_data": "unknown",
        "coauthor_unpublished": "unknown",
        "private": private,
    }


def add_file(
    root: Path,
    src: Path,
    *,
    kind: str = "file",
    private: bool = False,
    external_api: str = "unknown",
) -> dict[str, Any]:
    data = load(root)
    mid = _next_id(data)
    subdir = "private" if private else "inbox"
    dest_dir = root / "materials" / subdir
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    shutil.copy2(src, dest)
    entry = {
        "id": mid,
        "kind": kind,
        "path": dest.relative_to(root).as_posix(),
        "sha256": file_hash(dest),
        "origin": {
            "provided_as": kind,
            "original_name": src.name,
            "provided_at": default_clock().now_rfc3339(),
        },
        "permissions": _permissions(private, external_api),
    }
    data["materials"].append(entry)
    save(root, data)
    return entry


def _records_from(
    parsed: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    link_duplicates(parsed)
    records: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    for rec in parsed:
        entry: dict[str, Any] = {"bib_key": rec["bib_key"], "metadata_status": "unresolved"}
        doi = rec.get("doi")
        if doi:
            if is_valid_doi(doi):
                entry["doi"] = normalize_doi(doi)
            else:
                findings.append(
                    {
                        "check_id": "materials.doi_malformed",
                        "severity": "minor",
                        "reason": f"malformed DOI {doi!r} in {rec['bib_key']}",
                    }
                )
        if rec.get("duplicate_of"):
            entry["duplicate_of"] = rec["duplicate_of"]
            findings.append(
                {
                    "check_id": "materials.duplicate_linked",
                    "severity": "info",
                    "reason": f"{rec['bib_key']} linked to {rec['duplicate_of']}",
                }
            )
        records.append(entry)
    return records, findings


def add_bibtex(root: Path, src: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    return _add_bibliographic(
        root, src, kind="bibtex", parsed=parse_bibtex(src.read_text(encoding="utf-8"))
    )


def add_ris(root: Path, src: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    return _add_bibliographic(
        root, src, kind="ris", parsed=parse_ris(src.read_text(encoding="utf-8"))
    )


def add_doi_list(root: Path, src: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    dois = parse_doi_list(src.read_text(encoding="utf-8"))
    parsed = [{"bib_key": f"doi{i + 1}", "doi": d} for i, d in enumerate(dois)]
    return _add_bibliographic(root, src, kind="doi_list", parsed=parsed)


def _add_bibliographic(
    root: Path, src: Path, *, kind: str, parsed: list[dict[str, Any]]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    data = load(root)
    mid = _next_id(data)
    dest_dir = root / "materials" / "inbox"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    shutil.copy2(src, dest)
    records, findings = _records_from(parsed)
    entry = {
        "id": mid,
        "kind": kind,
        "path": dest.relative_to(root).as_posix(),
        "sha256": file_hash(dest),
        "origin": {
            "provided_as": kind,
            "original_name": src.name,
            "provided_at": default_clock().now_rfc3339(),
        },
        "permissions": _permissions(False),
        "records": records,
    }
    data["materials"].append(entry)
    save(root, data)
    return entry, findings
