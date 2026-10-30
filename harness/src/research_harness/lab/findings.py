"""Synthesis findings for the writer (``lab/findings.yaml``): statements with
evidence refs, handed over only when every central claim has a counter-evidence
record (FR-29, T60). Central claims are the ones the protocol/caller marks central.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from research_harness.lab.counter import covered_claims


def findings_path(root: Path) -> Path:
    return root / "lab" / "findings.yaml"


def load_findings(root: Path) -> dict[str, Any]:
    path = findings_path(root)
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def set_findings(
    root: Path, items: list[dict[str, Any]], *, central_claims: list[str]
) -> list[dict[str, Any]]:
    """Store findings for the writer, unless a central claim lacks counter-evidence."""
    findings: list[dict[str, Any]] = []
    covered = covered_claims(root)
    for claim in central_claims:
        if claim not in covered:
            findings.append(
                {
                    "check_id": "findings.counter_missing",
                    "severity": "blocker",
                    "reason": f"central claim {claim!r} has no counter-evidence record",
                    "location": {"ref": claim},
                    "proposed_action": "",
                }
            )
    if findings:
        return findings

    findings_path(root).parent.mkdir(parents=True, exist_ok=True)
    findings_path(root).write_text(
        yaml.safe_dump(
            {"central_claims": central_claims, "findings": items},
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return findings
