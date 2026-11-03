"""Figure placement and rendering for the manuscript (M4-14, FR-43).

A unit body places a figure with a marker ``{{fig:FIG-001}}`` bound to a figure
record (built from real result rows — M3-20/ADR-009 — never fabricated, H6). On
assembly the markers are numbered by first appearance and replaced with the image
plus a numbered caption («Рис. N. …»). Integration findings mirror the cross-ref
check: a marker with no record is ``figure.unresolved_ref``; a figure that is
never placed is ``figure.unreferenced``; a placed figure whose image is not built
is ``figure.not_built``. Nothing is invented.

Not in this slice: author-supplied binary assets (``kind: image``/``table`` with
an asset/rights record, M3-12) and the empirical ≥1-figure readiness tie-in
(ADR-023); this slice lands chart figures, placement, numbering and the checks.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from research_harness.analysis import figures

_FIG = re.compile(r"\{\{fig:(FIG-\d+)\}\}")


def referenced_ids(bodies: list[str]) -> list[str]:
    """Figure ids referenced across the bodies, in order of first appearance."""
    order: list[str] = []
    seen: set[str] = set()
    for body in bodies:
        for m in _FIG.finditer(body):
            fid = m.group(1)
            if fid not in seen:
                seen.add(fid)
                order.append(fid)
    return order


def _caption_line(n: int, rec: dict[str, Any]) -> str:
    caption = rec.get("caption", "")
    return f"*Рис. {n}. {caption}*".replace(" .", ".").rstrip()


def bind(root: Path, bodies: list[str]) -> tuple[list[str], list[dict[str, Any]]]:
    """Replace figure markers with image + numbered caption; return (bodies, gaps)."""
    order = referenced_ids(bodies)
    records = {fid: figures.load(root, fid) for fid in order}
    resolved = [fid for fid in order if records[fid] is not None]
    numbers = {fid: i + 1 for i, fid in enumerate(resolved)}
    gaps: list[dict[str, Any]] = []

    def repl(m: re.Match[str]) -> str:
        fid = m.group(1)
        rec = records.get(fid)
        if rec is None:
            return "[рисунок відсутній]"
        n = numbers[fid]
        img = figures.image_path(root, fid)
        parts: list[str] = []
        if img.is_file():
            alt = rec.get("alt", rec.get("caption", fid))
            parts.append(f"![{alt}]({img.resolve()})")
        parts.append(_caption_line(n, rec))
        return "\n\n".join(parts)

    rendered = [_FIG.sub(repl, body) for body in bodies]

    for fid in order:
        if records[fid] is None:
            gaps.append(_g("figure.unresolved_ref", f"{{{{fig:{fid}}}}} has no figure record", fid))
        elif not figures.image_path(root, fid).is_file():
            gaps.append(_g("figure.not_built", f"{fid} is placed but its image is not built", fid))

    placed = set(order)
    for fid in figures.list_ids(root):
        if fid not in placed:
            gaps.append(_g("figure.unreferenced", f"{fid} is defined but never placed", fid))

    return rendered, gaps


def _g(check_id: str, reason: str, fig_id: str) -> dict[str, Any]:
    action = {
        "figure.unresolved_ref": "Fix the marker or define the figure.",
        "figure.not_built": "Build the figure (rh figure build) before export.",
        "figure.unreferenced": "Place the figure with {{fig:ID}} or remove it.",
    }.get(check_id, "")
    return {
        "check_id": check_id,
        "severity": "major",
        "reason": reason,
        "location": {"ref": f"figure:{fig_id}"},
        "proposed_action": action,
    }
