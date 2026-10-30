"""Submit reviewer verdicts (v0): a verdict may never exceed the deterministic
support cap; coverage is checked/denominator with unchecked claims listed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from research_harness.claims import ledger as ledger_mod
from research_harness.claims.support import compute_support
from research_harness.core.clock import default_clock
from research_harness.review.handoff import _write as write_handoff
from research_harness.review.handoff import load as load_handoff

_RANK = {"unreviewed": 0, "insufficient": 1, "partial": 2, "supported": 3}
_MATERIAL = ("critical", "material")


def submit(
    root: Path, review_id: str, *, verdicts: list[dict[str, Any]], findings: list[dict[str, Any]]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Store verdicts as claim assessments; reject any that exceed the cap."""
    handoff = load_handoff(root, review_id)
    unit_id = handoff["target"]
    claims = {c["id"]: c for c in ledger_mod.load_unit_claims(root, unit_id)}
    problems: list[dict[str, Any]] = []

    # Reject verdicts that violate caps (nothing stored on violation).
    for v in verdicts:
        claim = claims.get(v["claim_id"])
        if claim is None:
            problems.append(_f("review.unknown_claim", f"{v['claim_id']} not in unit {unit_id}"))
            continue
        trial = dict(claim)
        trial["assessments"] = [
            *claim.get("assessments", []),
            {
                "support": v["support"],
                "rationale": v["rationale"],
                "by": handoff["role"],
                "at": default_clock().now_rfc3339(),
            },
        ]
        capped, _ = compute_support(root, trial)
        if _RANK.get(v["support"], 0) > _RANK.get(capped, 0):
            problems.append(
                _f(
                    "review.verdict_cap_exceeded",
                    f"{v['claim_id']}: verdict {v['support']!r} exceeds cap {capped!r}",
                )
            )
    if problems:
        return handoff, problems

    # Apply: append each assessment, let the ledger re-cap and store.
    for v in verdicts:
        claim = claims[v["claim_id"]]
        claim.setdefault("assessments", []).append(
            {
                "support": v["support"],
                "rationale": v["rationale"],
                "by": handoff["role"],
                "at": default_clock().now_rfc3339(),
            }
        )
    ledger_mod.set_claims(root, unit_id, list(claims.values()))

    handoff["status"] = "submitted"
    handoff["verdicts"] = verdicts
    handoff["findings"] = findings
    write_handoff(root, handoff)
    return handoff, []


def coverage(root: Path, unit_id: str) -> dict[str, Any]:
    claims = ledger_mod.load_unit_claims(root, unit_id)
    material = [c for c in claims if c["materiality"] in _MATERIAL]
    checked = [c for c in material if c.get("assessments")]
    unchecked = [c["id"] for c in material if not c.get("assessments")]
    return {
        "checked": len(checked),
        "denominator": len(material),
        "unchecked_claims": unchecked,
    }


def _f(check_id: str, reason: str) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "severity": "blocker",
        "reason": reason,
        "location": {},
        "proposed_action": "",
    }
