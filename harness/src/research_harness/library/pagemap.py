"""Map PDF page numbers to printed page numbers (02 §12 ``page_map``).

Offset from the source's ``pages.first`` when known; otherwise inferred from
running-header/footer page numbers. A single consistent offset →
``pdf_to_printed_offset``; varying offsets → an ``explicit`` list; neither →
``unknown`` (then locators use ``pdf_page`` only and the quote check reports
``quote.printed_page_unknown``).
"""

from __future__ import annotations

import re
from typing import Any

from research_harness.library.extract import PageText

_PAGE_NUMBER = re.compile(r"^\d{1,4}$")


def _detect_page_number(text: str) -> int | None:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return None
    for candidate in (lines[0], lines[-1]):
        if _PAGE_NUMBER.match(candidate):
            return int(candidate)
    return None


def build_page_map(pages: list[PageText], first_printed: int | None = None) -> dict[str, Any]:
    if first_printed is not None:
        return {"pdf_to_printed_offset": first_printed - 1}
    detected = [(p.pdf_page, _detect_page_number(p.text)) for p in pages]
    offsets = {printed - pdf for pdf, printed in detected if printed is not None}
    if not offsets:
        return {"unknown": True}
    if len(offsets) == 1:
        return {"pdf_to_printed_offset": next(iter(offsets))}
    return {
        "explicit": [
            {"pdf_page": pdf, "printed_page": str(printed)}
            for pdf, printed in detected
            if printed is not None
        ]
    }


def printed_for(page_map: dict[str, Any], pdf_page: int) -> str | None:
    if "pdf_to_printed_offset" in page_map:
        return str(pdf_page + page_map["pdf_to_printed_offset"])
    if "explicit" in page_map:
        for entry in page_map["explicit"]:
            if entry["pdf_page"] == pdf_page:
                return entry["printed_page"]
    return None


def pdf_for_printed(page_map: dict[str, Any], printed_page: str) -> int | None:
    if "pdf_to_printed_offset" in page_map:
        try:
            return int(printed_page) - page_map["pdf_to_printed_offset"]
        except ValueError:
            return None
    if "explicit" in page_map:
        for entry in page_map["explicit"]:
            if entry["printed_page"] == str(printed_page):
                return entry["pdf_page"]
    return None


def apply_page_map(pages: list[PageText], page_map: dict[str, Any]) -> None:
    """Annotate each PageText with its printed page (in place)."""
    for p in pages:
        p.printed_page = printed_for(page_map, p.pdf_page)
