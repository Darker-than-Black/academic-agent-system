"""Extraction matrix (``lab/matrix.jsonl``): one row per source per question,
with the data basis, limitations and the excerpt(s) it rests on (02 §12).

A review statement with no excerpt is a finding (T30), not a silent claim.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_harness.core.clock import default_clock
from research_harness.evidence import PRODUCER
from research_harness.schemas import validate


def matrix_path(root: Path) -> Path:
    return root / "lab" / "matrix.jsonl"


def load_rows(root: Path) -> list[dict[str, Any]]:
    path = matrix_path(root)
    if not path.is_file():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def _next_id(root: Path) -> str:
    nums = [int(r["id"].split("-")[1]) for r in load_rows(root) if r["id"].startswith("MR-")]
    return f"MR-{(max(nums) + 1 if nums else 1):04d}"


def add_row(
    root: Path,
    *,
    source_id: str,
    question_id: str,
    statement: str,
    data_basis: str,
    limitations: str,
    excerpt_ids: list[str] | None = None,
    position: str | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    excerpt_ids = excerpt_ids or []
    findings: list[dict[str, Any]] = []
    if not excerpt_ids:
        findings.append(
            {
                "check_id": "matrix.no_excerpt",
                "severity": "major",
                "reason": f"matrix statement for {source_id} rests on no excerpt",
                "location": {"ref": f"source:{source_id}"},
                "proposed_action": "",
            }
        )

    row: dict[str, Any] = {
        "schema_version": "0.2",
        "id": _next_id(root),
        "created_at": default_clock().now_rfc3339(),
        "producer": PRODUCER,
        "source_id": source_id,
        "question_id": question_id,
        "statement": statement,
        "data_basis": data_basis,
        "limitations": limitations,
        "excerpt_ids": excerpt_ids,
    }
    if position is not None:
        row["position"] = position

    errors = validate("matrix-row", row)
    if errors:
        raise ValueError(f"invalid matrix row: {errors}")
    path = matrix_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row, findings
