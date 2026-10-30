"""Unit/chapter summaries, document map, glossary (M2-08).

A summary is valid only for the text hash it records; any text change makes the
unit summary, its chapter summary and map.md stale, and integration-level work
never runs on stale summaries (summaries-context.md; FR-47, T51).
"""

from __future__ import annotations

SHEET_CHARS = 40000  # one author's sheet (FR-47)
