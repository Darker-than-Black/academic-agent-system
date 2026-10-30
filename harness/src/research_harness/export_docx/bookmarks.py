"""Bookmark names for units and paragraphs (applied to the .docx by the pandoc
filter / python-docx post-processing; recorded in the export manifest)."""

from __future__ import annotations

from pathlib import Path

from research_harness.structure import ops
from research_harness.units import anchors
from research_harness.units.write import read_body


def bookmark_map(root: Path) -> dict[str, str]:
    """{unit_id|paragraph_id: bookmark_name} for every unit and paragraph."""
    out: dict[str, str] = {}
    for uid, folder in ops.current_folders(root).items():
        out[uid] = f"unit_{uid}"
        if (folder / "text.md").is_file():
            for pid in anchors.paragraph_map(read_body(root, uid)):
                out[pid] = f"para_{pid}"
    return out
