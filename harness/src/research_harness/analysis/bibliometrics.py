"""Corpus bibliometrics input (M3-21, FR-54 p.3).

Keyword co-occurrence, clusters and time trends are computed by sandbox scripts
(``rh analysis run``), never by this core. This module only exposes the
literature registry metadata those scripts read, as
``analysis/data/corpus-metadata.json`` — titles, years, venues and keywords, no
foreign full text (H8)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_harness.sources import registry


def corpus_metadata(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rec in registry.load(root):
        rows.append(
            {
                "id": rec.get("id"),
                "title": rec.get("title"),
                "year": rec.get("year"),
                "container": rec.get("container"),
                "authors": rec.get("author"),
                "keywords": rec.get("keywords", []),
            }
        )
    return rows


def export(root: Path) -> dict[str, Any]:
    rows = corpus_metadata(root)
    out = root / "analysis" / "data" / "corpus-metadata.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"path": str(out.relative_to(root)), "n": len(rows)}
