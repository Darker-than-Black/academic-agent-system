"""Reviewer handoffs (``review/<REVIEW-id>.json``): prepare a request + pack,
and load it back (05-agents.md)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_harness.context import pack as pack_mod
from research_harness.core.clock import default_clock
from research_harness.schemas import validate

_ROLE = {"unit": "unit_critic", "article": "integration_critic"}
_PACK_ROLE = {"unit": "unit_critic", "article": "analyst"}


def review_dir(root: Path) -> Path:
    d = root / "review"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _next_id(root: Path) -> str:
    d = root / "review"
    n = len(list(d.glob("REVIEW-*.json"))) + 1 if d.is_dir() else 1
    return f"REVIEW-{n}"


def load(root: Path, review_id: str) -> dict[str, Any]:
    return json.loads((root / "review" / f"{review_id}.json").read_text(encoding="utf-8"))


def _write(root: Path, record: dict[str, Any]) -> dict[str, Any]:
    errors = validate("handoff", record)
    if errors:
        raise ValueError(f"invalid handoff: {errors}")
    review_dir(root)
    (root / "review" / f"{record['id']}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return record


def prepare(root: Path, level: str, *, unit: str | None = None) -> dict[str, Any]:
    target = unit if level == "unit" else "article"
    pack_target = unit if level == "unit" else (unit or "")
    pack_id = ""
    if pack_target:
        manifest, _ = pack_mod.build_pack(root, pack_target, _PACK_ROLE[level])
        pack_id = manifest["id"]
    record = {
        "schema_version": "0.2",
        "id": _next_id(root),
        "level": level,
        "target": target,
        "role": _ROLE[level],
        "context_pack_id": pack_id,
        "status": "prepared",
        "created_at": default_clock().now_rfc3339(),
    }
    return _write(root, record)
