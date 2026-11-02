"""Object autonomy level and gate-skip enforcement (lifecycle-records.md; M3-06).

Autonomy (FR-33) governs when `rh` hands control back to the author:
- ``step``  — after every stage.
- ``gates`` — only at gates and human decisions (the default, ADR-015).
- ``batch`` — questions queue in ``next_actions``; stages continue until a gate.

On every level, G0–G3 / GE, finding resolutions and external actions require the
author: a stage that needs a gate cannot proceed without a recorded approval,
whatever the autonomy level (ASR-04). This module holds the level and the pure
gate-skip predicate; it never records a gate itself (H14).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_harness.state.snapshot import atomic_write_bytes

LEVELS = ("step", "gates", "batch")
DEFAULT = "gates"


def _object_path(root: Path) -> Path:
    return root / "object.json"


def _load(root: Path) -> dict[str, Any]:
    return json.loads(_object_path(root).read_text(encoding="utf-8"))


def read(root: Path) -> str:
    """Current autonomy level (default ``gates``)."""
    return _load(root).get("autonomy", DEFAULT)


def set_level(root: Path, level: str) -> str:
    """Persist a new autonomy level into object.json. Raises on an unknown level."""
    if level not in LEVELS:
        raise ValueError(f"unknown autonomy level: {level!r}")
    obj = _load(root)
    obj["autonomy"] = level
    atomic_write_bytes(
        _object_path(root), (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )
    return level


def gate_skip_finding(required_gate: str, approved_gates: set[str]) -> dict[str, Any] | None:
    """A blocker when a stage needs ``required_gate`` but it has no valid approval
    — the same at every autonomy level (FR-33). ``None`` when the gate is met."""
    if required_gate in approved_gates:
        return None
    return {
        "check_id": "lifecycle.autonomy_gate_skip",
        "severity": "blocker",
        "reason": f"stage requires gate {required_gate} but it has no valid approval",
        "location": {},
        "observed": required_gate,
        "proposed_action": f"Record {required_gate} in your own terminal first.",
    }
