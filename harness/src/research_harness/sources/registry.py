"""Source registry (``sources/registry.jsonl``) — 02 §12, 04-modules/sources-library.md.

Identity first (invariant 1): a source exists as a record before any excerpt
points to it; a DOI is optional. Records are appended, then deduplicated by
linking (never merging). Author names are parsed into ``{family, given}`` and a
romanized sort key (KMU 2010) is derived for Cyrillic-aware sorting (T43).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from research_harness import __version__
from research_harness.core.clock import default_clock
from research_harness.core.translit_uk import is_cyrillic, transliterate
from research_harness.materials.doi_list import is_valid_doi, normalize_doi
from research_harness.sources.dedup import link_duplicates
from research_harness.state.snapshot import atomic_write_bytes

_AUTHOR_SPLIT = re.compile(r"\s+and\s+|;", re.IGNORECASE)
_INITIAL = re.compile(r"^[^\W\d_]\.?$", re.UNICODE)  # single letter + optional dot


def _parse_no_comma(name: str) -> dict[str, str]:
    """Parse a comma-less author token into ``{family, given?}``.

    Handles both ``Given Family`` and the Scopus ``Family I. I.`` surname-first
    initials form by treating a trailing run of single-letter initials as the
    given name and the remaining leading tokens as the family.
    """
    parts = name.split()
    if len(parts) == 1:
        return {"family": parts[0]}
    trailing = len(parts)
    while trailing > 1 and _INITIAL.match(parts[trailing - 1]):
        trailing -= 1
    if 0 < trailing < len(parts):  # leading words + trailing initials → "Family I. I."
        return {"family": " ".join(parts[:trailing]), "given": " ".join(parts[trailing:])}
    return {"family": parts[-1], "given": " ".join(parts[:-1])}  # "Given Family"


def registry_path(root: Path) -> Path:
    return root / "sources" / "registry.jsonl"


def load(root: Path) -> list[dict[str, Any]]:
    path = registry_path(root)
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def _write_all(root: Path, records: list[dict[str, Any]]) -> None:
    body = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in records)
    atomic_write_bytes(registry_path(root), body.encode("utf-8"))


def _next_id(records: list[dict[str, Any]]) -> str:
    nums = [int(r["id"].split("-", 1)[1]) for r in records if r.get("id", "").startswith("S-")]
    return f"S-{(max(nums) + 1) if nums else 1:04d}"


def parse_authors(author: str | None) -> list[dict[str, str]]:
    """Parse a BibTeX/RIS author string into ``[{family, given?}]``.

    Accepts ``Family, Given`` and ``Given Family`` tokens separated by ``and``
    or ``;``. Cyrillic names are kept verbatim; romanization is derived on read.
    """
    if not author:
        return []
    authors: list[dict[str, str]] = []
    for token in _AUTHOR_SPLIT.split(author):
        name = token.strip()
        if not name:
            continue
        if "," in name:
            family, _, given = name.partition(",")
            entry = {"family": family.strip()}
            if given.strip():
                entry["given"] = given.strip()
        else:
            entry = _parse_no_comma(name)
        authors.append(entry)
    return authors


def romanized_name(entry: dict[str, str]) -> str:
    """Family[, given] romanized (KMU 2010) for sorting/matching; ASCII left as-is."""
    family = entry.get("family", "")
    given = entry.get("given", "")
    fam = transliterate(family) if is_cyrillic(family) else family
    giv = transliterate(given) if is_cyrillic(given) else given
    return f"{fam}, {giv}".strip(", ")


def sort_key(record: dict[str, Any]) -> tuple[str, str]:
    """Registry/reference sort key: romanized first-author family, then title."""
    authors = record.get("authors") or []
    first = romanized_name(authors[0]).lower() if authors else "￿"
    return (first, (record.get("title") or "").lower())


def _year_to_int(year: Any) -> int | None:
    if year is None:
        return None
    m = re.search(r"\d{4}", str(year))
    return int(m.group(0)) if m else None


def build_source(
    rec: dict[str, Any],
    *,
    source_id: str,
    metadata_sources: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a schema-valid Source dict from a parsed/looked-up record."""
    now = default_clock().now_rfc3339()
    doi = rec.get("doi")
    source: dict[str, Any] = {
        "schema_version": "0.2",
        "id": source_id,
        "created_at": now,
        "producer": {"kind": "tool", "name": "rh", "version": __version__},
        "title": rec.get("title") or "",
        "type": (rec.get("type") or "unknown"),
        "metadata_status": rec.get("metadata_status", "unresolved"),
        "access_level": rec.get("access_level", "metadata"),
        "retraction": {"status": "unknown", "checked_at": now},
        "bib_key": rec.get("bib_key") or source_id,
        "authors": parse_authors(rec.get("author")) if "authors" not in rec else rec["authors"],
    }
    year = _year_to_int(rec.get("year"))
    if year is not None:
        source["year"] = year
    if doi and is_valid_doi(doi):
        source["doi"] = normalize_doi(doi)
    if rec.get("url"):
        source["url"] = rec["url"]
    if rec.get("container"):
        source["container"] = rec["container"]
    if rec.get("issn"):
        source["issn"] = rec["issn"]
    if rec.get("language"):
        source["language"] = rec["language"]
    if rec.get("identifiers"):
        source["identifiers"] = rec["identifiers"]
    if metadata_sources:
        source["metadata_sources"] = metadata_sources
    return source


def add_records(
    root: Path,
    parsed: list[dict[str, Any]],
    *,
    metadata_sources: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Append new Source records, link duplicates, persist; return (added, findings)."""
    records = load(root)
    added: list[dict[str, Any]] = []
    for rec in parsed:
        sid = _next_id(records + added)
        added.append(build_source(rec, source_id=sid, metadata_sources=metadata_sources))

    findings: list[dict[str, Any]] = []
    # Link duplicates across the whole (existing + new) set; only annotate new ones.
    all_records = records + added
    link_duplicates(all_records)
    existing_ids = {r["id"] for r in records}
    for rec in all_records:
        if rec["id"] in existing_ids:
            continue
        dup = rec.pop("duplicate_of", None)
        if dup:
            rec.setdefault("links", []).append({"relation": "duplicate_of", "source_id": dup})
            findings.append(
                {
                    "check_id": "source.duplicate_unlinked",
                    "severity": "info",
                    "reason": f"{rec['id']} linked as duplicate_of {dup}",
                    "location": {"ref": f"source:{rec['id']}"},
                    "proposed_action": "",
                }
            )
    _write_all(root, records + added)
    return added, findings


def get(root: Path, source_id: str) -> dict[str, Any] | None:
    for rec in load(root):
        if rec.get("id") == source_id:
            return rec
    return None


def update(root: Path, source_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    """Apply ``patch`` to a source record and persist. Returns the updated record."""
    records = load(root)
    updated: dict[str, Any] | None = None
    for rec in records:
        if rec.get("id") == source_id:
            rec.update(patch)
            updated = rec
            break
    if updated is None:
        raise KeyError(source_id)
    _write_all(root, records)
    return updated


def link(root: Path, src_id: str, dst_id: str, relation: str) -> dict[str, Any]:
    """Add a typed link (duplicate_of / preprint_of / published_version_of)."""
    records = load(root)
    found: dict[str, Any] | None = None
    ids = {r["id"] for r in records}
    for missing in (src_id, dst_id):
        if missing not in ids:
            raise KeyError(missing)
    for rec in records:
        if rec["id"] == src_id:
            rec.setdefault("links", []).append({"relation": relation, "source_id": dst_id})
            found = rec
            break
    assert found is not None
    _write_all(root, records)
    return found
