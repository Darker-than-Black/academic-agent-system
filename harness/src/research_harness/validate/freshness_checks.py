"""Freshness-scope check: report stale artifacts (02 §6, FR-10, T09).

Runs when ``ctx.extra["object_root"]`` is set (the resolved object folder). A
stale artifact is reported as a ``minor`` finding, never a blocker: staleness is
a state to surface, not an input error.
"""

from __future__ import annotations

from pathlib import Path

from research_harness.state.freshness import compute_stale, kind_from_id
from research_harness.validate.framework import Finding, ValidationContext, finding, registry

CHECK_ID = "freshness.stale"


@registry.register(id=CHECK_ID, version="1", scope="freshness")
def _freshness_check(ctx: ValidationContext) -> list[Finding]:
    root = ctx.extra.get("object_root")
    if root is None:
        return []
    findings: list[Finding] = []
    for ref in sorted(compute_stale(Path(root))):
        kind, _, rid = ref.partition(":")
        findings.append(
            finding(
                check_id=CHECK_ID,
                severity="minor",
                reason=f"{kind} {rid} is stale: an artifact it depends on changed",
                ref=ref,
                proposed_action="Re-derive the artifact, then checkpoint.",
            )
        )
    return findings


__all__ = ["CHECK_ID", "kind_from_id"]
