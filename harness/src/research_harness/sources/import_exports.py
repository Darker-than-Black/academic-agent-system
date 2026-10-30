"""Manual-export importers: Scopus (RIS/CSV), WoS (RIS), Google Scholar (RIS),
Zotero (BibTeX). Reuses the dependency-free BibTeX/RIS parsers (02 §9.2) and
adds a Scopus CSV reader. Each importer yields parsed records in the shape the
registry consumes (``title``, ``author`` string, ``year``, ``doi``, ``url`` …).
"""

from __future__ import annotations

import csv
import io
from typing import Any

from research_harness.materials.bib import parse_bibtex
from research_harness.materials.ris import parse_ris

# Which parser each manual source uses by default (06-research-agent §3.1).
_FORMAT_BY_SOURCE = {
    "zotero": "bibtex",
    "scholar": "ris",
    "wos": "ris",
    "scopus": "auto",  # ris or csv, detected from content
    "ris": "ris",
    "bibtex": "bibtex",
    "csv": "csv",
}

# Scopus CSV column -> our field (headers as exported by Scopus).
_SCOPUS_CSV = {
    "Authors": "author",
    "Title": "title",
    "Year": "year",
    "DOI": "doi",
    "Source title": "container",
    "Link": "url",
    "ISSN": "issn",
    "Abstract": "abstract",
}


def _parse_scopus_csv(text: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    reader = csv.DictReader(io.StringIO(text))
    for i, row in enumerate(reader, start=1):
        rec: dict[str, Any] = {"bib_key": f"scopus{i}"}
        for col, field in _SCOPUS_CSV.items():
            val = (row.get(col) or "").strip()
            if not val:
                continue
            if field == "author":
                rec["author"] = val.replace("; ", "; ")
            elif field == "issn":
                rec["issn"] = [val]
            else:
                rec[field] = val
        records.append(rec)
    return records


def _detect_scopus(text: str) -> str:
    head = text.lstrip()
    if head.startswith("TY  -") or "\nTY  -" in text[:200]:
        return "ris"
    return "csv"


def parse_export(from_source: str, text: str) -> tuple[list[dict[str, Any]], str]:
    """Return (parsed records, format used). Raises KeyError for an unknown source."""
    fmt = _FORMAT_BY_SOURCE[from_source]
    if fmt == "auto":
        fmt = _detect_scopus(text)
    if fmt == "bibtex":
        return parse_bibtex(text), "bibtex"
    if fmt == "ris":
        return parse_ris(text), "ris"
    if fmt == "csv":
        return _parse_scopus_csv(text), "csv"
    raise KeyError(from_source)
