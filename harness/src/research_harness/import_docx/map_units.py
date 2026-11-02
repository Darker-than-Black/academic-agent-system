"""Map parsed changes to the object's current units and paragraphs.

A change is *mapped* when its ``unit_id`` resolves to a current unit folder;
otherwise it is *unmapped* (the editor deleted the bookmark, or wrote outside any
unit). Unmapped changes are never dropped — they are recorded and raise a
blocker (T46). Mapping does not require the paragraph to still exist: a change
whose paragraph bookmark is gone still maps to its unit and is shown there.
"""

from __future__ import annotations

from pathlib import Path

from research_harness.import_docx.parse import Change
from research_harness.structure import ops


def map_changes(root: Path, changes: list[Change]) -> tuple[list[Change], list[Change]]:
    folders = ops.current_folders(root)
    mapped: list[Change] = []
    unmapped: list[Change] = []
    for c in changes:
        if c.unit_id and c.unit_id in folders:
            mapped.append(c)
        else:
            unmapped.append(c)
    return mapped, unmapped
