"""Saturation tracking (FR-56). Themes are counted across matrix rows in the
order they were added, grouped into batches; when the trailing ``stop_after``
batches add no new theme, a saturation stop is proposed (not recorded — the
author or the search module decides).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from research_harness.lab.matrix import load_rows


def _theme(row: dict[str, Any]) -> str:
    return row.get("position") or row.get("question_id") or row.get("statement", "")


def check(root: Path, *, batch_size: int = 10, stop_after: int = 2) -> dict[str, Any]:
    rows = load_rows(root)
    seen: set[str] = set()
    new_per_batch: list[int] = []
    batches: list[list[str]] = []
    for i in range(0, len(rows), batch_size):
        chunk = rows[i : i + batch_size]
        new_here = []
        for row in chunk:
            theme = _theme(row)
            if theme and theme not in seen:
                seen.add(theme)
                new_here.append(theme)
        new_per_batch.append(len(new_here))
        batches.append(new_here)

    propose_stop = len(new_per_batch) >= stop_after and all(
        n == 0 for n in new_per_batch[-stop_after:]
    )
    return {
        "batch_size": batch_size,
        "stop_after": stop_after,
        "batches": len(new_per_batch),
        "new_per_batch": new_per_batch,
        "new_themes_per_batch": batches,
        "total_themes": len(seen),
        "propose_stop": propose_stop,
        "reason": "saturation" if propose_stop else "",
    }
