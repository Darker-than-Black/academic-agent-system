"""Inject the review methodology into the methods section on export (M4-17/M4-12).

The author places a marker ``{{methodology}}`` in the methods unit body; on
assembly it is replaced with the rendered methodology (selection criteria, search
summary, included-studies table) from the review-methodology record (M4-17). This
mirrors how the references-kind unit is filled with the numbered bibliography
(M4-16), but uses an in-text marker because there is no ``methods`` unit kind and
``structure.yaml`` is not hand-edited (H13).

Findings: a ``{{methodology}}`` marker with nothing to render is
``methodology.marker_empty``; a methodology record that exists but is never placed
is ``methodology.unplaced`` — both major, both only name a gap, nothing invented.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from research_harness.export_docx import citations
from research_harness.methodology import record as methodology

MARKER = "{{methodology}}"


def inject(root: Path, bodies: list[str]) -> list[str]:
    """Replace the methodology marker in each body with the rendered methods block."""
    if not any(MARKER in b for b in bodies):
        return list(bodies)
    # Number the included-sources table with the same citation numbers the
    # bibliography uses, so its № column matches the in-text [n] markers.
    cite_numbers = citations.allocate_number_map(root, bodies)
    rendered_methods = methodology.methods_markdown(root, cite_numbers=cite_numbers)
    return [b.replace(MARKER, rendered_methods) if MARKER in b else b for b in bodies]


def gaps(root: Path, bodies: list[str]) -> list[dict[str, Any]]:
    placed = any(MARKER in b for b in bodies)
    findings: list[dict[str, Any]] = []
    if placed and not methodology.methods_markdown(root).strip():
        findings.append(
            _g(
                "methodology.marker_empty",
                "{{methodology}} is placed but there is nothing to render "
                "(no record, criteria, search log or corpus)",
                "Record the methodology (rh methodology set) or remove the marker.",
            )
        )
    if not placed and methodology.load(root) is not None:
        findings.append(
            _g(
                "methodology.unplaced",
                "a review methodology record exists but is not placed in the methods section",
                "Add {{methodology}} to the methods unit, or remove the record.",
            )
        )
    return findings


def _g(check_id: str, reason: str, action: str) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "severity": "major",
        "reason": reason,
        "location": {},
        "proposed_action": action,
    }
