"""Research gaps (``lab/gaps.yaml``). Each gap carries evidence refs validated
against matrix rows, excerpts and sources (shared check in positions.py).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from research_harness.lab.positions import validate_refs


def gaps_path(root: Path) -> Path:
    return root / "lab" / "gaps.yaml"


def set_gaps(root: Path, gaps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings = validate_refs(root, gaps, "gaps")
    if not any(f["severity"] in ("blocker", "major") for f in findings):
        gaps_path(root).parent.mkdir(parents=True, exist_ok=True)
        gaps_path(root).write_text(
            yaml.safe_dump({"gaps": gaps}, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
    return findings
