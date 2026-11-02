"""Unit locks (lifecycle-records.md; M3-08, FR-41, T21).

A locked unit cannot be written — by the agent or by ``rh`` — even when the
author asks; the author must ``rh unlock`` it first (02 §5.6 rule 4). ``unlock``
is human-only (the CLI enforces the TTY rule); ``assert_not_locked`` is called
from every write path.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_harness.core.clock import default_clock
from research_harness.core.errors import BlockedError, InvalidInputError
from research_harness.schemas import validate
from research_harness.state.snapshot import atomic_write_bytes


def locks_path(root: Path) -> Path:
    return root / "locks.json"


def load(root: Path) -> dict[str, dict[str, Any]]:
    p = locks_path(root)
    if not p.is_file():
        return {}
    data = json.loads(p.read_text(encoding="utf-8"))
    return data.get("locks", {}) if isinstance(data, dict) else {}


def _write(root: Path, locks: dict[str, dict[str, Any]]) -> None:
    body = json.dumps({"schema_version": "0.2", "locks": locks}, ensure_ascii=False, indent=2)
    atomic_write_bytes(locks_path(root), (body + "\n").encode("utf-8"))


def is_locked(root: Path, unit_id: str) -> bool:
    return unit_id in load(root)


def lock(root: Path, unit_id: str, *, reason: str, locked_by: str) -> dict[str, Any]:
    locks = load(root)
    rec = {
        "unit_id": unit_id,
        "reason": reason,
        "locked_by": locked_by,
        "at": default_clock().now_rfc3339(),
    }
    if validate("unit-lock", rec):
        raise InvalidInputError("error.unit_lock_invalid")
    locks[unit_id] = rec
    _write(root, locks)
    return rec


def unlock(root: Path, unit_id: str) -> bool:
    locks = load(root)
    existed = locks.pop(unit_id, None) is not None
    if existed:
        _write(root, locks)
    return existed


def assert_not_locked(root: Path, unit_id: str) -> None:
    """Raise BlockedError (exit 3) if the unit is locked (T21)."""
    if is_locked(root, unit_id):
        raise BlockedError("error.unit_locked")
