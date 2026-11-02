"""Result rows (M3-19, analysis-sandbox.md). A run's structured output
(``outputs/rows.json``) becomes validated result rows in ``results/rows.jsonl``,
each with an ``RR-<run>-<seq>`` id. Rows are append-only; a re-run writes new
rows under a new run id (invariant 5)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_harness.core.clock import default_clock
from research_harness.schemas import validate

_AGENT = {"kind": "model", "name": "analysis", "version": "0.1.0"}


def rows_path(root: Path) -> Path:
    return root / "results" / "rows.jsonl"


def load(root: Path) -> list[dict[str, Any]]:
    path = rows_path(root)
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def by_id(root: Path) -> dict[str, dict[str, Any]]:
    return {r["id"]: r for r in load(root)}


def _run_seq(run_id: str) -> str:
    return run_id.split("-")[1]


def append_from_output(
    root: Path, run_id: str, output: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Validate each output row, assign an id, and append to rows.jsonl."""
    created: list[dict[str, Any]] = []
    now = default_clock().now_rfc3339()
    run_seq = _run_seq(run_id)
    start = sum(1 for r in load(root) if r["run_id"] == run_id)
    for i, raw in enumerate(output, start=start + 1):
        row: dict[str, Any] = {
            "schema_version": "0.2",
            "id": f"RR-{run_seq}-{i:04d}",
            "created_at": now,
            "producer": _AGENT,
            "run_id": run_id,
            "variable_or_metric": raw["variable_or_metric"],
            "value": raw["value"],
            "unit": raw["unit"],
            "aggregation": raw["aggregation"],
        }
        for opt in ("dataset_id", "subset", "condition", "weights", "n", "uncertainty", "derived"):
            if opt in raw and raw[opt] is not None:
                row[opt] = raw[opt]
        errors = validate("result-row", row)
        if errors:
            raise ValueError(f"invalid result row from output[{i}]: {errors}")
        created.append(row)

    path = rows_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for row in created:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return created
