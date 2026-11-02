"""Ethics gate GE enforcement (lifecycle-records.md; M3-07, FR-31).

If intake has participants = true (Q7), or participants is unknown for an
empirical study kind (Q5), stage A6 (evidence collection) is blocked until an
external approval exists with gate GE, ``actor_role: ethics_committee``, an
approve decision, and a document (T33). Synthetic participants never satisfy
this (analysis-sandbox.md, FR-59) — only a real committee approval does.

This module reads intake answers and the approvals log; it never records a gate.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_harness.gates.records import approvals_path
from research_harness.intake import answers as answers_mod

EMPIRICAL_KINDS = {"empirical_quantitative", "empirical_qualitative", "mixed"}
_APPROVE = {"approved", "approved_with_conditions"}
_UNKNOWN = (None, "unknown")


def _value(data: dict[str, Any], qid: str) -> Any:
    entry = data.get("answers", {}).get(qid)
    return entry.get("value") if isinstance(entry, dict) else "unknown"


def requires_ethics(data: dict[str, Any]) -> bool:
    """True when A6 needs a GE ethics approval, per Q7 (+ Q5 for unknown)."""
    participants = _value(data, "Q7")
    if participants is True:
        return True
    if participants in _UNKNOWN and _value(data, "Q5") in EMPIRICAL_KINDS:
        return True
    return False


def has_ethics_approval(root: Path) -> bool:
    """A recorded external GE approval from an ethics committee, with a document."""
    path = approvals_path(root)
    if not path.is_file():
        return False
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (
            rec.get("gate") == "GE"
            and rec.get("decision") in _APPROVE
            and rec.get("actor_role") == "ethics_committee"
            and rec.get("document")
        ):
            return True
    return False


def ethics_gate_finding(root: Path) -> dict[str, Any] | None:
    """A blocker for A6 when ethics approval is required but not present."""
    data = answers_mod.load(root)
    if not requires_ethics(data):
        return None
    if has_ethics_approval(root):
        return None
    return {
        "check_id": "lifecycle.ethics_missing",
        "severity": "blocker",
        "reason": "A6 (evidence collection) needs an external GE ethics-committee approval first",
        "location": {},
        "observed": "A6",
        "proposed_action": "Obtain ethics approval and record GE with the committee's document.",
    }
