"""Screening decisions (``lab/screening.jsonl``): include/exclude with a reason.

A decision without a reason is a finding (02-lifecycle A2).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_harness.core.clock import default_clock


def screening_path(root: Path) -> Path:
    return root / "lab" / "screening.jsonl"


def screen(
    root: Path, source_id: str, *, include: bool, reason: str
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    if not reason.strip():
        findings.append(
            {
                "check_id": "screening.decision_without_reason",
                "severity": "major",
                "reason": f"{source_id}: screening decision has no reason",
                "location": {"ref": f"source:{source_id}"},
                "proposed_action": "",
            }
        )
    entry = {
        "id": source_id,
        "decision": "include" if include else "exclude",
        "reason": reason,
        "at": default_clock().now_rfc3339(),
    }
    path = screening_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry, findings


def load_screening(root: Path) -> list[dict[str, Any]]:
    path = screening_path(root)
    if not path.is_file():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
