"""Position map (``lab/positions.yaml``).

Every position carries evidence refs; a ref that points at no matrix row,
excerpt or source is a finding (no claim without evidence). The shared ref
check (``validate_refs``) is reused by the gaps module.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from research_harness.evidence.excerpts import load_excerpts
from research_harness.lab.matrix import load_rows
from research_harness.sources import registry


def positions_path(root: Path) -> Path:
    return root / "lab" / "positions.yaml"


def _known_refs(root: Path) -> set[str]:
    refs: set[str] = set()
    for r in load_rows(root):
        refs.add(f"matrix:{r['id']}")
    for e in load_excerpts(root):
        refs.add(f"excerpt:{e['id']}")
    for s in registry.load(root):
        refs.add(f"source:{s['id']}")
    return refs


def validate_refs(root: Path, items: list[dict[str, Any]], what: str) -> list[dict[str, Any]]:
    known = _known_refs(root)
    findings: list[dict[str, Any]] = []
    for item in items:
        for ref in item.get("evidence_refs", []):
            if ref not in known:
                findings.append(
                    {
                        "check_id": f"{what}.unknown_ref",
                        "severity": "major",
                        "reason": f"{what} evidence ref {ref!r} points at nothing",
                        "location": {},
                        "proposed_action": "",
                    }
                )
    return findings


def set_positions(root: Path, positions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings = validate_refs(root, positions, "positions")
    if not any(f["severity"] in ("blocker", "major") for f in findings):
        positions_path(root).parent.mkdir(parents=True, exist_ok=True)
        positions_path(root).write_text(
            yaml.safe_dump({"positions": positions}, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
    return findings
