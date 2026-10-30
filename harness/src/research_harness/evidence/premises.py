"""Premises and definitions (``lab/premises.jsonl``). Each rests on a source
excerpt or is explicitly flagged as an assumption; otherwise it is a finding
(T30), never silently accepted (H6).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_harness.core.clock import default_clock
from research_harness.evidence import PRODUCER
from research_harness.schemas import validate


def premises_path(root: Path) -> Path:
    return root / "lab" / "premises.jsonl"


def load_premises(root: Path) -> list[dict[str, Any]]:
    path = premises_path(root)
    if not path.is_file():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def _next_id(root: Path, kind: str) -> str:
    prefix = "DEF" if kind == "definition" else "P"
    width = 3 if kind == "definition" else 4
    nums = [
        int(p["id"].split("-")[1]) for p in load_premises(root) if p["id"].startswith(prefix + "-")
    ]
    return f"{prefix}-{(max(nums) + 1 if nums else 1):0{width}d}"


def add_premise(
    root: Path,
    *,
    statement: str,
    kind: str = "premise",
    term: str | None = None,
    excerpt_ids: list[str] | None = None,
    assumption: bool = False,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Record a premise/definition. No excerpt and not an assumption → finding."""
    excerpt_ids = excerpt_ids or []
    if not excerpt_ids and not assumption:
        finding = {
            "check_id": "premise.no_basis",
            "severity": "major",
            "reason": (
                f"premise {statement!r} has no source excerpt and is not flagged as an assumption"
            ),
            "location": {},
            "proposed_action": "",
        }
        return None, [finding]

    premise: dict[str, Any] = {
        "schema_version": "0.2",
        "id": _next_id(root, kind),
        "created_at": default_clock().now_rfc3339(),
        "producer": PRODUCER,
        "kind": kind,
        "statement": statement,
    }
    if term is not None:
        premise["term"] = term
    if excerpt_ids:
        premise["excerpt_ids"] = excerpt_ids
    if assumption:
        premise["assumption"] = True

    errors = validate("premise", premise)
    if errors:
        raise ValueError(f"invalid premise: {errors}")
    path = premises_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(premise, ensure_ascii=False) + "\n")
    return premise, []
