"""Deterministic article format findings (M4-12, FR-12; ADR-022 presentation).

The reference document (``rulepacks/<pack>/reference.docx``) carries the visual
format (Times New Roman 14 pt, 1.5 spacing, 1.25 cm indent, A4, 2 cm margins,
centred page number); pandoc renders against it. This module adds the one
deterministic format check that does not need the rendered file: a page-count
estimate against the cat. «Б» ``≤ 20 pages`` limit. Per ADR-022 it is a ``major``
finding (informational for a draft), never a blocker, and never fabricated — it
is a transparent chars → A4-pages estimate at the profile. Thresholds mirror
``rulepacks/ua-fahove-b/rules/format.yaml`` (data, draft).
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

# A filled A4 page at TNR 14 / 1.5 spacing / 2 cm margins holds ~1800 characters
# (the common Ukrainian «сторінка ≈ 1800 знаків» convention). Draft default.
DEFAULT_CHARS_PER_PAGE = 1800
DEFAULT_MAX_PAGES = 20


def page_estimate(root: Path, *, chars_per_page: int = DEFAULT_CHARS_PER_PAGE) -> int:
    """Estimated A4 page count from the assembled manuscript character count."""
    from research_harness.export_docx import assemble

    chars = len(assemble.assemble_markdown(root))
    if chars <= 0:
        return 0
    return math.ceil(chars / max(chars_per_page, 1))


def volume_findings(
    root: Path,
    *,
    max_pages: int = DEFAULT_MAX_PAGES,
    chars_per_page: int = DEFAULT_CHARS_PER_PAGE,
) -> list[dict[str, Any]]:
    """A major (non-blocking) finding when the estimate exceeds the page limit."""
    est = page_estimate(root, chars_per_page=chars_per_page)
    if est <= max_pages:
        return []
    return [
        {
            "check_id": "format.volume",
            "severity": "major",
            "reason": (
                f"estimated ~{est} A4 pages (> {max_pages}) at the cat. «Б» profile "
                f"(≈{chars_per_page} chars/page)"
            ),
            "location": {},
            "observed": est,
            "expected": f"<= {max_pages}",
            "proposed_action": "Shorten the manuscript, or confirm the venue's page limit.",
        }
    ]
