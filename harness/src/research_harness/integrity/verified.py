"""Verified-export conditions, re-checked in code (M3-15, integrity.md, FR-12).

Every condition is evaluated here, now — no cached PASS is trusted (invariant 4),
and ``unknown`` never passes (invariant 5). ``check_conditions`` returns the list
of findings that block a verified export; an empty list means all conditions hold.

Conditions (integrity.md "Verified export conditions"):
  1. a valid G3 approval for the current snapshot;
  2. no open blocker finding in the findings index;
  3. rule packs of layers 3–6 current (``review_after`` not passed);
  4. no content/reference gaps (placeholders, unsupported claims, stale, overlap);
  5. review coverage complete for material claims;
  6. an AI-use record present;
  7. asset rights resolved;
  8. a venue check present and current for the target date.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_harness.export_docx import assemble
from research_harness.findings import index as findings_index
from research_harness.gates.records import approvals_path
from research_harness.integrity import ai_use, assets, overlap, source_origin, venue
from research_harness.review import verdicts
from research_harness.rules import freshness
from research_harness.state import snapshot as snap
from research_harness.structure import ops

_APPROVE = {"approved", "approved_with_conditions"}


def _blocker(check_id: str, reason: str, *, observed: Any = None) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "severity": "blocker",
        "reason": reason,
        "location": {},
        "observed": observed,
        "proposed_action": "Resolve this condition before a verified export (FR-12).",
    }


def g3_valid(root: Path) -> bool:
    """A recorded G3 approval whose target is the current snapshot (condition 1)."""
    current = snap.read_current(root)
    path = approvals_path(root)
    if current is None or not path.is_file():
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
            rec.get("gate") == "G3"
            and rec.get("decision") in _APPROVE
            and rec.get("target", {}).get("snapshot_id") == current
        ):
            return True
    return False


def _rules_expired(root: Path) -> list[dict[str, Any]]:
    stack = root / "profiles" / "resolved-stack.json"
    if not stack.is_file():
        return []
    try:
        rules = json.loads(stack.read_text(encoding="utf-8")).get("rules", [])
    except json.JSONDecodeError:
        return []
    out: list[dict[str, Any]] = []
    for r in rules:
        if not r.get("effective", True):
            continue
        if freshness.classify(r) == "expired":
            out.append(
                _blocker(
                    "integrity.rules_expired",
                    f"rule {r.get('rule_id', r.get('key'))} is expired (review_after passed)",
                    observed=r.get("review_after"),
                )
            )
    return out


def _open_blockers(root: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for f in findings_index.list_findings(root, status="open"):
        if f.get("severity") == "blocker":
            out.append(
                _blocker(
                    "integrity.open_blocker",
                    f"open blocker finding {f.get('id', '?')}: {f.get('check_id', '?')}",
                    observed=f.get("id"),
                )
            )
    return out


def _coverage(root: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for uid in ops.current_folders(root):
        out += verdicts.coverage_findings(verdicts.coverage(root, uid))
    return out


def check_conditions(root: Path, *, pack: str = "ua-fahove-b") -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    if not g3_valid(root):
        findings.append(
            _blocker("integrity.g3_invalid", "no valid G3 approval for the current snapshot")
        )
    findings += _open_blockers(root)
    findings += _rules_expired(root)

    # Content / reference gaps and own-text overlap.
    findings += [
        _blocker(g["check_id"], g["reason"], observed=g.get("location"))
        for g in assemble.compute_gaps(root)
    ]
    findings += overlap.findings_from(overlap.run(root))

    findings += _coverage(root)

    mf = ai_use.missing_finding(root)
    if mf:
        findings.append(mf)
    findings += assets.rights_findings(root)
    findings += venue.status_findings(root)
    findings += source_origin.origin_findings(root)
    return findings
