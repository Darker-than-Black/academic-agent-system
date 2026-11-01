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
from research_harness.schemas import validate

_RANK = {"unreviewed": 0, "insufficient": 1, "partial": 2, "supported": 3}
_MATERIAL = ("critical", "material")


def _assessment(v: dict[str, Any], by: str) -> dict[str, Any]:
    """Build the stored assessment from a submitted verdict, carrying the M3-02
    fields (evidence_refs, access_level, confidence) when present."""
    a: dict[str, Any] = {
        "support": v["support"],
        "rationale": v["rationale"],
        "by": by,
        "at": default_clock().now_rfc3339(),
    }
    for key in ("evidence_refs", "access_level", "confidence"):
        if v.get(key) is not None:
            a[key] = v[key]
    return a


def submit(
    root: Path, review_id: str, *, verdicts: list[dict[str, Any]], findings: list[dict[str, Any]]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Store verdicts as claim assessments; reject any that exceed the cap."""
    handoff = load_handoff(root, review_id)
    unit_id = handoff["target"]
    claims = {c["id"]: c for c in ledger_mod.load_unit_claims(root, unit_id)}
    problems: list[dict[str, Any]] = []

    # Reject verdicts that are malformed, lack evidence, or exceed caps
    # (nothing is stored on any violation).
    for v in verdicts:
        cid = v.get("claim_id", "?")
        # Invariant 3: a non-unreviewed verdict needs >= 1 evidence ref (FR-07).
        if v.get("support") != "unreviewed" and not v.get("evidence_refs"):
            problems.append(
                _f("review.verdict_without_evidence", f"{cid}: verdict has no evidence ref")
            )
            continue
        verr = validate("verdict", v)
        if verr:
            problems.append(_f("review.verdict_invalid", f"{cid}: {verr[0]}"))
            continue
        claim = claims.get(v["claim_id"])
        if claim is None:
            problems.append(_f("review.unknown_claim", f"{v['claim_id']} not in unit {unit_id}"))
            continue
        trial = dict(claim)
        trial["assessments"] = [*claim.get("assessments", []), _assessment(v, handoff["role"])]
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
        claim.setdefault("assessments", []).append(_assessment(v, handoff["role"]))
    ledger_mod.set_claims(root, unit_id, list(claims.values()))

    handoff["status"] = "submitted"
    handoff["verdicts"] = verdicts
    handoff["findings"] = findings
    write_handoff(root, handoff)
    return handoff, []


def coverage(root: Path, unit_id: str) -> dict[str, Any]:
    """Coverage of material claims by verdict; denominator = all material claims
    in scope (invariant 4). A run that checked fewer than all is ``partial``,
    never PASS; zero checked is ``unknown`` (N3)."""
    claims = ledger_mod.load_unit_claims(root, unit_id)
    material = [c for c in claims if c["materiality"] in _MATERIAL]
    checked = [c for c in material if c.get("assessments")]
    unchecked = [c["id"] for c in material if not c.get("assessments")]
    by_verdict: dict[str, int] = {}
    for c in checked:
        support = c.get("support", "unreviewed")
        by_verdict[support] = by_verdict.get(support, 0) + 1
    if not material:
        status = "ok"
    elif not checked:
        status = "unknown"
    elif unchecked:
        status = "partial"
    else:
        status = "ok"
    return {
        "checked": len(checked),
        "denominator": len(material),
        "unchecked_claims": unchecked,
        "by_verdict": by_verdict,
        "status": status,
    }


def coverage_findings(cov: dict[str, Any]) -> list[dict[str, Any]]:
    """A non-blocking finding when coverage is incomplete (major; a blocker for
    verified export, FR-09/N3)."""
    if cov["status"] in ("partial", "unknown"):
        return [
            {
                "check_id": "review.coverage_incomplete",
                "severity": "major",
                "reason": (
                    f"{cov['checked']} of {cov['denominator']} material claims checked"
                    f" ({cov['status']}); unchecked: {', '.join(cov['unchecked_claims']) or 'none'}"
                ),
                "location": {},
                "proposed_action": "Review the unchecked claims before export.",
            }
        ]
    return []


def _f(check_id: str, reason: str) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "severity": "blocker",
        "reason": reason,
        "location": {},
        "proposed_action": "",
    }
