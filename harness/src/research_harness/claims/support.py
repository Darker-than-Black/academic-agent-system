"""Deterministic support caps (claims-text.md). Applied before any stored
verdict; a cap can only lower support, never raise it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from research_harness.evidence.excerpts import load_excerpts
from research_harness.sources import registry

# Orderable supports for capping. Hard states (not_found/contradicted/
# unverifiable) are handled separately and are not part of this ranking.
_RANK = {"unreviewed": 0, "insufficient": 1, "partial": 2, "supported": 3}
_NAME = {0: "unreviewed", 1: "insufficient", 2: "partial", 3: "supported"}


def _desired(claim: dict[str, Any]) -> str:
    assessments = claim.get("assessments") or []
    if assessments:
        return assessments[-1]["support"]
    return claim.get("support", "unreviewed")


def compute_support(root: Path, claim: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    """Return the capped support for a claim and any findings raised."""
    findings: list[dict[str, Any]] = []
    excerpt_idx = {e["id"]: e for e in load_excerpts(root)}
    evidence = claim.get("evidence", [])
    cid = claim.get("id", "C-?")

    explicit_sources: set[str] = set()  # cited directly as evidence
    excerpt_sources: set[str] = set()  # reached via an excerpt
    excerpt_results: list[str] = []
    has_excerpt = False
    abstract_only = True
    for ev in evidence:
        if ev["type"] == "excerpt":
            exc = excerpt_idx.get(ev["id"])
            if exc is None:
                continue
            has_excerpt = True
            excerpt_sources.add(exc["source_id"])
            if exc["access_level"] in ("fulltext", "local_original"):
                abstract_only = False
            excerpt_results.append(exc.get("quote_check", {}).get("result", "unknown"))
        elif ev["type"] == "source":
            explicit_sources.add(ev["id"])

    # A directly cited source that is missing or not_found blocks the claim.
    for sid in explicit_sources:
        rec = registry.get(root, sid)
        if rec is None or rec.get("metadata_status") == "not_found":
            findings.append(_finding(cid, "cited source not_found or missing from the registry"))
            return "not_found", findings
        if (rec.get("retraction") or {}).get("status") == "notice_found":
            findings.append(_finding(cid, "cited source has a retraction notice"))
            return "not_found", findings
    # A source reached via an excerpt blocks only on an explicit not_found/retraction.
    for sid in excerpt_sources:
        rec = registry.get(root, sid)
        if rec is None:
            continue
        if rec.get("metadata_status") == "not_found":
            findings.append(_finding(cid, "excerpt source is not_found"))
            return "not_found", findings
        if (rec.get("retraction") or {}).get("status") == "notice_found":
            findings.append(_finding(cid, "excerpt source has a retraction notice"))
            return "not_found", findings

    # Level caps.
    max_level = 3
    if not evidence:
        max_level = 1  # no evidence -> insufficient
    elif has_excerpt and abstract_only:
        max_level = 1  # only abstract-level excerpts -> insufficient
    if any(r == "fail" for r in excerpt_results):
        max_level = min(max_level, 2)  # failed quote check -> partial at most
    if not any(r == "pass" for r in excerpt_results):
        max_level = min(
            max_level, 2
        )  # no explicit, quote-checked statement -> never supported (N1)

    desired = _desired(claim)
    if desired not in _RANK:  # a hard state the author set deliberately
        return desired, findings
    if _RANK[desired] > max_level:
        capped = _NAME[max_level]
        findings.append(
            {
                "check_id": "claims.support_cap_exceeded",
                "severity": "blocker",
                "reason": f"{cid}: support {desired!r} exceeds the deterministic cap {capped!r}",
                "location": {"ref": f"claim:{cid}"},
                "proposed_action": "",
            }
        )
        return capped, findings
    return desired, findings


def _finding(cid: str, reason: str) -> dict[str, Any]:
    return {
        "check_id": "claims.material_without_evidence",
        "severity": "blocker",
        "reason": f"{cid}: {reason}",
        "location": {"ref": f"claim:{cid}"},
        "proposed_action": "",
    }
