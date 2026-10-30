"""Excerpts (``lab/excerpts.jsonl``): exact quoted spans with a locator, access
level and a deterministic quote check (M2-02). FR-30, T30.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_harness.core.clock import default_clock
from research_harness.core.hashing import canonical_json_hash
from research_harness.evidence import PRODUCER
from research_harness.library.extract import load_pagetext
from research_harness.library.quotes import check_quote
from research_harness.schemas import validate
from research_harness.sources import registry


def excerpts_path(root: Path) -> Path:
    return root / "lab" / "excerpts.jsonl"


def load_excerpts(root: Path) -> list[dict[str, Any]]:
    path = excerpts_path(root)
    if not path.is_file():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def _next_id(root: Path) -> str:
    nums = [int(e["id"].split("-")[1]) for e in load_excerpts(root)]
    return f"E-{(max(nums) + 1 if nums else 1):05d}"


def _source_sha(root: Path, source_id: str) -> str:
    """Hash of the text the excerpt was taken against (never invented, H6)."""
    rec = registry.get(root, source_id) or {}
    ft = rec.get("fulltext") or {}
    if ft.get("sha256"):
        return ft["sha256"]
    pt = root / "sources" / "pagetext" / f"{source_id}.jsonl"
    if pt.is_file():
        from research_harness.core.hashing import file_hash

        return file_hash(pt)
    return canonical_json_hash(rec)


def add_excerpt(
    root: Path,
    *,
    source_id: str,
    text: str,
    locator: dict[str, Any],
    access_level: str,
    extraction_method: str = "manual",
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Record an excerpt and run its quote check against the local page text."""
    findings: list[dict[str, Any]] = []
    pages = load_pagetext(root, source_id)
    qr = check_quote(pages, source_id=source_id, text=text, locator=locator)
    if qr.finding:
        findings.append(qr.finding)

    excerpt = {
        "schema_version": "0.2",
        "id": _next_id(root),
        "created_at": default_clock().now_rfc3339(),
        "producer": PRODUCER,
        "source_id": source_id,
        "source_sha256": _source_sha(root, source_id),
        "text": text,
        "locator": {k: v for k, v in locator.items() if v is not None},
        "access_level": access_level,
        "extraction_method": extraction_method,
        "quote_check": {"result": qr.result, "checked_at": default_clock().now_rfc3339()},
    }
    errors = validate("excerpt", excerpt)
    if errors:
        raise ValueError(f"invalid excerpt: {errors}")
    path = excerpts_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(excerpt, ensure_ascii=False) + "\n")
    return excerpt, findings
