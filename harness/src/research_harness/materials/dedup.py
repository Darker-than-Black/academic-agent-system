"""Duplicate detection; duplicates are LINKED, never merged (02 §9.2, FR-36).

Clean-room implementation (not adapted from OpenDraft): DOI, URL and
normalized title+author-year matching. A preprint and its published version are
linked via ``duplicate_of``, keeping both records.
"""

from __future__ import annotations

import re
from typing import Any

from research_harness.materials.doi_list import is_valid_doi, normalize_doi

_WORD = re.compile(r"\w+", re.UNICODE)


def _norm_title(title: str | None) -> str:
    if not title:
        return ""
    return " ".join(_WORD.findall(title.lower()))


def _first_author(author: str | None) -> str:
    if not author:
        return ""
    first = re.split(r"\s+and\s+|;", author)[0]
    return _WORD.findall(first.lower())[0] if _WORD.findall(first.lower()) else ""


def _signature(rec: dict[str, Any]) -> tuple[str, str, str, str]:
    doi = normalize_doi(rec["doi"]) if rec.get("doi") and is_valid_doi(rec["doi"]) else ""
    url = (rec.get("url") or "").strip().lower()
    return (
        doi,
        url,
        _norm_title(rec.get("title")),
        f"{_first_author(rec.get('author'))}|{rec.get('year') or ''}",
    )


def link_duplicates(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Set ``duplicate_of`` on later records that match an earlier one."""
    seen_doi: dict[str, str] = {}
    seen_url: dict[str, str] = {}
    seen_ta: dict[str, str] = {}
    for rec in records:
        doi, url, title, ta = _signature(rec)
        match = None
        if doi and doi in seen_doi:
            match = seen_doi[doi]
        elif url and url in seen_url:
            match = seen_url[url]
        elif title and f"{title}|{ta}" in seen_ta:
            match = seen_ta[f"{title}|{ta}"]
        if match and match != rec["bib_key"]:
            rec["duplicate_of"] = match
        else:
            if doi:
                seen_doi.setdefault(doi, rec["bib_key"])
            if url:
                seen_url.setdefault(url, rec["bib_key"])
            if title:
                seen_ta.setdefault(f"{title}|{ta}", rec["bib_key"])
    return records
