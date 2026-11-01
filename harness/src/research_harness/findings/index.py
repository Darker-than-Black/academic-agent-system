"""Finding index store (`findings/index.jsonl`), append-only resolutions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_harness.core.clock import default_clock

STATUSES = ("open", "accepted", "rejected", "fixed", "unresolved")
_DECISION_STATUS = {"accept": "accepted", "reject": "rejected", "fixed": "fixed"}


def index_path(root: Path) -> Path:
    d = root / "findings"
    d.mkdir(parents=True, exist_ok=True)
    return d / "index.jsonl"


def load(root: Path) -> list[dict[str, Any]]:
    path = index_path(root)
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def _write(root: Path, entries: list[dict[str, Any]]) -> None:
    index_path(root).write_text(
        "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries), encoding="utf-8"
    )


def _next_id(entries: list[dict[str, Any]]) -> str:
    return f"F-{len(entries) + 1}"


def add(root: Path, finding: dict[str, Any], *, review_id: str | None = None) -> dict[str, Any]:
    """Append one finding to the index with status ``open``."""
    entries = load(root)
    entry = {
        "id": _next_id(entries),
        "check_id": finding.get("check_id", "unknown"),
        "severity": finding.get("severity", "info"),
        "review_id": review_id,
        "status": "open",
        "finding": finding,
        "resolutions": [],
    }
    entries.append(entry)
    _write(root, entries)
    return entry


def list_findings(root: Path, *, status: str | None = None) -> list[dict[str, Any]]:
    entries = load(root)
    return [e for e in entries if status is None or e["status"] == status]


def resolve(
    root: Path, finding_id: str, *, decision: str, reason: str | None, by: str
) -> dict[str, Any]:
    """Record a human resolution (append-only). Reject requires a reason (T13)."""
    if decision not in _DECISION_STATUS:
        raise ValueError(f"unknown decision: {decision!r}")
    if decision == "reject" and not (reason and reason.strip()):
        raise ValueError("reject requires a reason")
    entries = load(root)
    for e in entries:
        if e["id"] == finding_id:
            e["status"] = _DECISION_STATUS[decision]
            e.setdefault("resolutions", []).append(
                {
                    "decision": decision,
                    "reason": reason or "",
                    "by": by,
                    "at": default_clock().now_rfc3339(),
                }
            )
            _write(root, entries)
            return e
    raise KeyError(finding_id)
