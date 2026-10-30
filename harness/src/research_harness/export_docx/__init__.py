"""Draft export (M2-12): assemble the manuscript in structure order, generate
references in the pack's style, list gaps, and render .docx (pandoc) or .md.

Zero fabricated sources: every cited key must resolve to a registry record whose
status is not ``not_found`` (H6, T43). Foreign full texts and private materials
never enter an export (H8).
"""

from __future__ import annotations
