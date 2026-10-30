"""Deterministic quote and excerpt verification, plus injection flagging.

Every quoted span is searched on its cited page after normalization; a quote
that spans a page break is accepted on page N∪(N+1) and recorded as such. Results
map to findings: ``quote.not_found_on_page`` (invented/inexact), ``quote.
locator_mismatch`` (found on another page), ``quote.printed_page_unknown`` (no
page map), ``quote.unverifiable`` (low-quality page). Instruction-like text in a
source is flagged ``source.injection_suspect`` and never acted on (H10).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from research_harness.library import normalize
from research_harness.library.extract import QUALITY_LOW, PageText, load_pagetext
from research_harness.library.pagemap import pdf_for_printed


@dataclass
class QuoteResult:
    result: str  # pass | fail | unknown
    finding: dict[str, Any] | None = None
    matched_pdf_page: int | None = None
    across_break: bool = False


def _finding(check_id: str, severity: str, sid: str, reason: str, **loc: Any) -> dict[str, Any]:
    location = {"ref": f"source:{sid}"}
    location.update(loc)
    return {
        "check_id": check_id,
        "severity": severity,
        "reason": reason,
        "location": location,
        "proposed_action": "",
    }


def _page(pages: list[PageText], pdf_page: int) -> PageText | None:
    for p in pages:
        if p.pdf_page == pdf_page:
            return p
    return None


def check_quote(
    pages: list[PageText],
    *,
    source_id: str,
    text: str,
    locator: dict[str, Any],
    page_map: dict[str, Any] | None = None,
) -> QuoteResult:
    """Verify one quoted span against the cited page."""
    target = locator.get("pdf_page")
    if target is None and locator.get("printed_page") is not None:
        if not page_map or "unknown" in page_map:
            return QuoteResult(
                "unknown",
                _finding(
                    "quote.printed_page_unknown",
                    "minor",
                    source_id,
                    f"printed page {locator['printed_page']} has no PDF mapping",
                ),
            )
        target = pdf_for_printed(page_map, str(locator["printed_page"]))
    if target is None:
        return QuoteResult(
            "fail",
            _finding("quote.not_found_on_page", "major", source_id, "no locator page given"),
        )

    cited = _page(pages, target)
    if cited is None:
        return QuoteResult(
            "fail",
            _finding(
                "quote.not_found_on_page",
                "major",
                source_id,
                f"page {target} not in library",
                pdf_page=target,
            ),
        )
    if cited.quality == QUALITY_LOW:
        return QuoteResult(
            "unknown",
            _finding(
                "quote.unverifiable",
                "minor",
                source_id,
                f"page {target} text quality too low to verify",
                pdf_page=target,
            ),
            matched_pdf_page=target,
        )

    if normalize.contains(cited.text, text):
        return QuoteResult("pass", matched_pdf_page=target)

    # Across a page break: join with the neighbour pages (±1), record it.
    for neighbour in (target + 1, target - 1):
        other = _page(pages, neighbour)
        if other is None:
            continue
        lo, hi = sorted((target, neighbour))
        joined = _page(pages, lo).text + "\n" + _page(pages, hi).text
        if normalize.contains(joined, text):
            return QuoteResult("pass", matched_pdf_page=target, across_break=True)

    # Found on a different page → locator mismatch.
    for p in pages:
        if p.pdf_page != target and p.quality != QUALITY_LOW and normalize.contains(p.text, text):
            return QuoteResult(
                "fail",
                _finding(
                    "quote.locator_mismatch",
                    "major",
                    source_id,
                    f"quote found on page {p.pdf_page}, cited {target}",
                    pdf_page=target,
                ),
                matched_pdf_page=p.pdf_page,
            )

    return QuoteResult(
        "fail",
        _finding(
            "quote.not_found_on_page",
            "major",
            source_id,
            f"quote not found on page {target}",
            pdf_page=target,
        ),
        matched_pdf_page=target,
    )


def check_excerpts(
    root: Path,
    excerpts: list[dict[str, Any]],
    *,
    page_maps: dict[str, dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Check a list of excerpts; return (results, findings)."""
    page_maps = page_maps or {}
    results: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    cache: dict[str, list[PageText]] = {}
    for exc in excerpts:
        sid = exc["source_id"]
        pages = cache.setdefault(sid, load_pagetext(root, sid))
        qr = check_quote(
            pages,
            source_id=sid,
            text=exc["text"],
            locator=exc.get("locator", {}),
            page_map=page_maps.get(sid),
        )
        results.append(
            {
                "source_id": sid,
                "result": qr.result,
                "matched_pdf_page": qr.matched_pdf_page,
                "across_break": qr.across_break,
            }
        )
        if qr.finding:
            findings.append(qr.finding)
    return results, findings


# --- Injection flagging (H10) ----------------------------------------------
_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(the\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(the\s+)?(above|previous)", re.IGNORECASE),
    re.compile(r"as\s+an?\s+ai\s+(language\s+)?model", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\b", re.IGNORECASE),
    re.compile(r"system\s*prompt", re.IGNORECASE),
    re.compile(r"\bнехтуй\s+попередн", re.IGNORECASE),
    re.compile(r"\bігноруй\s+(усі\s+|всі\s+)?попередн", re.IGNORECASE),
]


def scan_injection(pages: list[PageText], source_id: str) -> list[dict[str, Any]]:
    """Flag instruction-like text found in a source (data only, never executed)."""
    findings: list[dict[str, Any]] = []
    for p in pages:
        for pattern in _INJECTION_PATTERNS:
            m = pattern.search(p.text)
            if m:
                findings.append(
                    _finding(
                        "source.injection_suspect",
                        "major",
                        source_id,
                        f"instruction-like text on page {p.pdf_page}: {m.group(0)!r}",
                        pdf_page=p.pdf_page,
                    )
                )
                break
    return findings
