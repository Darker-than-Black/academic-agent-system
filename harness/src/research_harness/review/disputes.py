"""Disputes between the analyst and a critic (review.md §Disputes; M3-05, FR-23).

Each side adds its argument and evidence once per cycle. After ``max_cycles``
(default 2) with no agreement the dispute becomes ``unresolved`` and goes to the
author; a dispute never auto-resolves to a pass (T23). Closing to
``resolved_by_author`` is a human decision (enforced in the CLI).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_harness.core.clock import default_clock
from research_harness.schemas import validate

DEFAULT_MAX_CYCLES = 2


def disputes_dir(root: Path) -> Path:
    d = root / "reviews" / "disputes"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _path(root: Path, dispute_id: str) -> Path:
    return disputes_dir(root) / f"{dispute_id}.json"


def load(root: Path, dispute_id: str) -> dict[str, Any]:
    return json.loads(_path(root, dispute_id).read_text(encoding="utf-8"))


def _write(root: Path, rec: dict[str, Any]) -> dict[str, Any]:
    errors = validate("dispute", rec)
    if errors:
        raise ValueError(f"invalid dispute: {errors}")
    _path(root, rec["id"]).write_text(
        json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return rec


def _next_id(root: Path) -> str:
    n = len(list(disputes_dir(root).glob("D-*.json"))) + 1
    return f"D-{n}"


def open_(
    root: Path, *, claim_id: str, finding_id: str, max_cycles: int = DEFAULT_MAX_CYCLES
) -> dict[str, Any]:
    rec = {
        "schema_version": "0.2",
        "id": _next_id(root),
        "claim_id": claim_id,
        "finding_id": finding_id,
        "cycles": [],
        "max_cycles": max_cycles,
        "status": "open",
    }
    return _write(root, rec)


def add_evidence(
    root: Path, dispute_id: str, *, by: str, argument: str, evidence_refs: list[str]
) -> dict[str, Any]:
    """Append one cycle. Refused once the dispute is closed or the cap is reached."""
    rec = load(root, dispute_id)
    if rec["status"] != "open":
        raise ValueError(f"dispute {dispute_id} is {rec['status']}, not open")
    if len(rec["cycles"]) >= rec["max_cycles"]:
        raise ValueError(f"dispute {dispute_id} reached max_cycles ({rec['max_cycles']})")
    rec["cycles"].append(
        {
            "by": by,
            "argument": argument,
            "evidence_refs": evidence_refs,
            "at": default_clock().now_rfc3339(),
        }
    )
    return _write(root, rec)


def cap_reached(rec: dict[str, Any]) -> bool:
    return len(rec["cycles"]) >= rec["max_cycles"]


def close(
    root: Path, dispute_id: str, *, status: str, author_decision: str | None = None
) -> dict[str, Any]:
    """Close a dispute as resolved_by_author or unresolved. Never auto-pass."""
    if status not in ("resolved_by_author", "unresolved"):
        raise ValueError(f"invalid close status: {status!r}")
    rec = load(root, dispute_id)
    rec["status"] = status
    if author_decision:
        rec["author_decision"] = author_decision
    return _write(root, rec)
