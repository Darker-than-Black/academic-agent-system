"""Source dedup over registry records: duplicates are LINKED, never merged.

Extends the materials-level matcher (DOI / URL / title+author) with
transliteration-insensitive normalization so a Cyrillic title and its romanized
form match (FR-36, T43). A preprint and its published version stay two records
linked by ``duplicate_of`` (02 §12 invariant 4).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from research_harness.core.translit_uk import transliterate
from research_harness.materials.doi_list import is_valid_doi, normalize_doi

_WORD = re.compile(r"\w+", re.UNICODE)


def _fold(text: str) -> str:
    """NFC, case-fold, transliterate Cyrillic, keep word tokens only."""
    text = unicodedata.normalize("NFC", text or "")
    text = transliterate(text)
    return " ".join(_WORD.findall(text.lower()))


def _title_of(rec: dict[str, Any]) -> str:
    return _fold(rec.get("title") or "")


def _first_author_token(rec: dict[str, Any]) -> str:
    authors = rec.get("authors") or []
    if authors:
        fam = authors[0].get("family") or ""
        tokens = _WORD.findall(_fold(fam))
        return tokens[0] if tokens else ""
    return ""


def _signature(rec: dict[str, Any]) -> tuple[str, str, str]:
    doi = ""
    raw_doi = rec.get("doi")
    if raw_doi and is_valid_doi(raw_doi):
        doi = normalize_doi(raw_doi)
    url = (rec.get("url") or "").strip().lower()
    year = rec.get("year")
    ta = f"{_title_of(rec)}|{_first_author_token(rec)}|{year if year is not None else ''}"
    return doi, url, ta


def link_duplicates(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Set ``duplicate_of`` (an id) on later records matching an earlier one.

    Matching precedence: DOI, then URL, then normalized title+first-author+year.
    The matched record's id is stored; callers turn it into a registry link.
    """
    seen_doi: dict[str, str] = {}
    seen_url: dict[str, str] = {}
    seen_ta: dict[str, str] = {}
    for rec in records:
        rid = rec["id"]
        doi, url, ta = _signature(rec)
        match = None
        if doi and doi in seen_doi:
            match = seen_doi[doi]
        elif url and url in seen_url:
            match = seen_url[url]
        elif ta.strip("|") and ta in seen_ta:
            match = seen_ta[ta]
        if match and match != rid:
            rec["duplicate_of"] = match
        else:
            if doi:
                seen_doi.setdefault(doi, rid)
            if url:
                seen_url.setdefault(url, rid)
            if ta.strip("|"):
                seen_ta.setdefault(ta, rid)
    return records
