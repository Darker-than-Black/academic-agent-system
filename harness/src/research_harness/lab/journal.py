"""Lab journal (``lablog/journal.jsonl``): append-only record of the research
cycle — questions, hypotheses, plan changes, dead ends, deviations, cost, model
IDs (FR-54 p.5). Append-only: a correction is a new line, never an edit.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_harness.core.clock import default_clock
from research_harness.core.ulid import new_ulid
from research_harness.schemas import validate


def journal_path(root: Path) -> Path:
    return root / "lablog" / "journal.jsonl"


def add(
    root: Path,
    kind: str,
    text: str,
    *,
    model_id: str | None = None,
    cost: float | str | None = None,
    refs: list[str] | None = None,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "id": "lj-" + new_ulid(),
        "at": default_clock().now_rfc3339(),
        "kind": kind,
        "text": text,
    }
    if model_id is not None:
        entry["model_id"] = model_id
    if cost is not None:
        entry["cost"] = cost
    if refs:
        entry["refs"] = refs
    errors = validate("lab-journal", entry)
    if errors:
        raise ValueError(f"invalid lab-journal line: {errors}")
    path = journal_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def load_journal(root: Path) -> list[dict[str, Any]]:
    path = journal_path(root)
    if not path.is_file():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
