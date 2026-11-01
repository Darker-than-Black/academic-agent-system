"""Ingest a source's legal full text into the page-accurate library.

Extracts per-page text, derives the page map (from ``pages.first`` or running
headers), writes ``sources/pagetext/<S>.jsonl``, stores the page map on the
source record, and flags any instruction-like text (H10). The FTS index is
rebuilt separately by :func:`research_harness.library.index.build_index`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from research_harness.library import index as index_mod
from research_harness.library.extract import extract_pages, write_pagetext
from research_harness.library.pagemap import apply_page_map, build_page_map
from research_harness.library.quotes import scan_injection
from research_harness.sources import registry


def _first_printed(source: dict[str, Any]) -> int | None:
    first = (source.get("pages") or {}).get("first")
    if first is None:
        return None
    try:
        return int(str(first))
    except ValueError:
        return None


def ingest_source(root: Path, source_id: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Extract and index one source's full text. Returns (source, injection findings)."""
    source = registry.get(root, source_id)
    if source is None:
        raise KeyError(source_id)
    fulltext = source.get("fulltext")
    if not fulltext or not fulltext.get("local_path"):
        raise ValueError(f"{source_id} has no local full text to ingest")
    pdf_path = root / fulltext["local_path"]
    with pdf_path.open("rb") as fh:
        header = fh.read(5)
    if header != b"%PDF-":
        # A fetched OA "PDF" is sometimes an HTML landing page; do not feed it to
        # the PDF parser (it would crash the whole index). H6: no fabricated text.
        raise ValueError(f"{source_id}: not a PDF (header {header!r})")
    pages = extract_pages(pdf_path)
    page_map = build_page_map(pages, _first_printed(source))
    apply_page_map(pages, page_map)
    write_pagetext(root, source_id, pages)
    source["page_map"] = page_map
    registry.update(root, source_id, source)
    return source, scan_injection(pages, source_id)


def ingest_all(root: Path) -> tuple[int, list[dict[str, Any]]]:
    """Ingest every source with a local full text, then rebuild the index."""
    findings: list[dict[str, Any]] = []
    n = 0
    for source in registry.load(root):
        if not source.get("fulltext", {}).get("local_path"):
            continue
        sid = source["id"]
        try:
            _src, fnd = ingest_source(root, sid)
        except Exception as exc:  # noqa: BLE001 - one unreadable file must not abort the index
            findings.append(
                {
                    "check_id": "library.unreadable_fulltext",
                    "severity": "warn",
                    "reason": f"{sid}: full text could not be extracted "
                    f"({type(exc).__name__}); skipped",
                    "location": {"ref": f"source:{sid}"},
                    "proposed_action": "replace with a real PDF or register the full text manually",
                }
            )
            continue
        findings.extend(fnd)
        n += 1
    index_mod.build_index(root)
    return n, findings
