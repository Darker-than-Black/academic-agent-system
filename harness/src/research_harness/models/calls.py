"""Model call log and pending downgrades (02 §10, NFR-05)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_harness.core.clock import default_clock
from research_harness.core.ulid import new_ulid

UNKNOWN = "unknown"


def _rh(root: Path) -> Path:
    d = root / ".rh"
    d.mkdir(parents=True, exist_ok=True)
    return d


def calls_path(root: Path) -> Path:
    return _rh(root) / "model-calls.jsonl"


def _pending_path(root: Path) -> Path:
    return _rh(root) / "pending-downgrades.json"


def record_downgrade(
    root: Path, role: str, *, from_tier: str, to_tier: str, reason: str
) -> dict[str, Any]:
    """Store a pending downgrade; the next log call for this role consumes it."""
    path = _pending_path(root)
    pending = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    entry = {"from_tier": from_tier, "to_tier": to_tier, "reason": reason}
    pending[role] = entry
    path.write_text(json.dumps(pending, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return entry


def _consume_downgrade(root: Path, role: str) -> dict[str, Any] | None:
    path = _pending_path(root)
    if not path.is_file():
        return None
    pending = json.loads(path.read_text(encoding="utf-8"))
    entry = pending.pop(role, None)
    path.write_text(json.dumps(pending, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return entry


def _next_id() -> str:
    return "mc-" + new_ulid()


def log_call(
    root: Path,
    *,
    host: str,
    role: str,
    tier_required: str,
    model_id: str,
    purpose: str = UNKNOWN,
    tokens_in: int | str = UNKNOWN,
    tokens_out: int | str = UNKNOWN,
    cost: float | str = UNKNOWN,
    duration_s: float | str = UNKNOWN,
    status: str = "ok",
    operation_id: str | None = None,
) -> dict[str, Any]:
    rec: dict[str, Any] = {
        "id": _next_id(),
        "at": default_clock().now_rfc3339(),
        "host": host,
        "role": role,
        "tier_required": tier_required,
        "model_id": model_id,
        "purpose": purpose,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost": cost,
        "duration_s": duration_s,
        "status": status,
    }
    downgrade = _consume_downgrade(root, role)
    if downgrade:
        rec["downgrade"] = downgrade
    if operation_id:
        rec["operation_id"] = operation_id
    with calls_path(root).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec
