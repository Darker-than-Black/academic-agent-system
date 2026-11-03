"""In-text citation binding and the numbered reference list (M4-16).

Drafting emits machine-readable cite markers ``[[cite:<bib_key>]]`` (optionally
with a locator: ``[[cite:<bib_key>|с. 25]]``) bound to a source-registry record.
On export the markers are numbered by first appearance across the manuscript and
rendered in text as ``[N]`` / ``[N, с. 25]``; the reference unit body is built as a
numbered "Список використаних джерел" in the same order. A cite key that resolves
to no usable record is a gap (``export.cite_unresolved``), never fabricated (H6).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from research_harness.sources import registry

# [[cite:key]] or [[cite:key|locator]]
_CITE = re.compile(r"\[\[cite:([^\]|]+?)(?:\|([^\]]+))?\]\]")


def _index(root: Path) -> dict[str, dict[str, Any]]:
    return {r["bib_key"]: r for r in registry.load(root) if r.get("bib_key")}


def render_text(text: str, numbers: dict[str, int], index: dict[str, dict[str, Any]]) -> str:
    """Replace cite markers in one text with ``[N]`` / ``[N, <locator>]``.

    Assumes every key already has a number (allocate_numbers ran first). An
    unresolved key renders as ``[?]`` and is reported as a gap elsewhere.
    """

    def repl(m: re.Match[str]) -> str:
        key = m.group(1).strip()
        locator = (m.group(2) or "").strip()
        rec = index.get(key)
        if rec is None or rec.get("metadata_status") == "not_found":
            return "[?]"
        n = numbers[key]
        return f"[{n}, {locator}]" if locator else f"[{n}]"

    return _CITE.sub(repl, text)


def allocate_numbers(bodies_in_order: list[str]) -> list[str]:
    """Return cited keys in order of first appearance across the given bodies."""
    order: list[str] = []
    seen: set[str] = set()
    for body in bodies_in_order:
        for m in _CITE.finditer(body):
            key = m.group(1).strip()
            if key not in seen:
                seen.add(key)
                order.append(key)
    return order


def _format_entry(rec: dict[str, Any]) -> str:
    """A plain reference-list entry (ДСТУ-like; exact punctuation is a preset)."""
    authors = "; ".join(
        f"{a.get('family', '')} {a.get('given', '')}".strip() for a in rec.get("authors", [])
    )
    parts: list[str] = []
    if authors:
        parts.append(authors.rstrip(".") + ".")
    title = rec.get("title")
    if title:
        parts.append(str(title) + ".")
    container = rec.get("container")
    if container:
        parts.append(str(container) + ".")
    year = rec.get("year")
    if year:
        parts.append(f"{year}.")
    doi = rec.get("doi")
    if doi:
        parts.append(f"DOI: {doi}.")
    return " ".join(parts).strip()


def bibliography_markdown(order: list[str], index: dict[str, dict[str, Any]]) -> str:
    """A numbered reference list for the resolved cited keys, in citation order."""
    lines: list[str] = []
    n = 0
    for key in order:
        rec = index.get(key)
        if rec is None or rec.get("metadata_status") == "not_found":
            continue
        n += 1
        lines.append(f"{n}. {_format_entry(rec)}")
    return "\n".join(lines)


def bind(root: Path, bodies_in_order: list[str]) -> tuple[list[str], str, list[dict[str, Any]]]:
    """Render cite markers across the manuscript bodies.

    Returns (rendered bodies in the same order, numbered bibliography markdown,
    gaps for unresolved cite keys).
    """
    index = _index(root)
    order = allocate_numbers(bodies_in_order)
    numbers = {key: i + 1 for i, key in enumerate(k for k in order if _resolved(index, k))}
    gaps: list[dict[str, Any]] = []
    for key in order:
        if not _resolved(index, key):
            gaps.append(
                {
                    "check_id": "export.cite_unresolved",
                    "severity": "blocker",
                    "reason": f"cited key {key!r} resolves to no usable registry record",
                    "location": {},
                    "proposed_action": "Add/resolve the source, or fix the cite key.",
                }
            )
    rendered = [render_text(b, numbers, index) for b in bodies_in_order]
    bib = bibliography_markdown([k for k in order if _resolved(index, k)], index)
    return rendered, bib, gaps


def _resolved(index: dict[str, dict[str, Any]], key: str) -> bool:
    rec = index.get(key)
    return rec is not None and rec.get("metadata_status") != "not_found"
