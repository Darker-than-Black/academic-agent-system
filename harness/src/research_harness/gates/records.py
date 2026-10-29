"""Approval records — append-only; written only by humans (02 §9.3)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

HUMAN = {"kind": "human", "name": "author", "version": "0.1.0"}


def approvals_path(root: Path) -> Path:
    return root / "approvals" / "approvals.jsonl"


def _next_id(root: Path) -> str:
    p = approvals_path(root)
    n = (
        sum(1 for _ in p.read_text(encoding="utf-8").splitlines() if _.strip()) + 1
        if p.is_file()
        else 1
    )
    return f"AP-{n:04d}"


def record(
    root: Path,
    gate: str,
    *,
    decision: str,
    reason: str,
    target: dict[str, Any],
    actor_role: str = "author",
    actor_label: str = "author",
    channel: str,
    conditions: str | None = None,
    document: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    ap_id = _next_id(root)
    rec: dict[str, Any] = {
        "id": ap_id,
        "gate": gate,
        "target": target,
        "decision": decision,
        "reason": reason,
        "actor_role": actor_role,
        "actor_label": actor_label,
        "channel": channel,
        "producer": HUMAN,
    }
    if request_id:
        rec["request_id"] = request_id
    if conditions:
        rec["conditions"] = conditions
    if document:
        rec["document"] = document

    p = approvals_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    if request_id:
        _mark_answered(root, request_id)
    return rec


def _mark_answered(root: Path, request_id: str) -> None:
    rf = root / "approvals" / "requests" / f"{request_id}.json"
    if rf.is_file():
        data = json.loads(rf.read_text(encoding="utf-8"))
        data["status"] = "answered"
        rf.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
