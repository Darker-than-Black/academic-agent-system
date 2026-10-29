"""Reference-scope checks: every ref resolves to a known artifact (02 §1.4)."""

from __future__ import annotations

from typing import Any

from research_harness.validate.framework import (
    Finding,
    ValidationContext,
    finding,
    registry,
)

CHECK_ID = "refs.unresolved"


def collect_refs(record: dict[str, Any]) -> list[str]:
    """Collect every artifact ref a record points at (inputs/dependencies/evidence)."""
    refs: list[str] = []
    for key in ("inputs", "dependencies"):
        for item in record.get(key, []) or []:
            if isinstance(item, dict) and "ref" in item:
                refs.append(item["ref"])
    for item in record.get("evidence", []) or []:
        if isinstance(item, dict) and "type" in item and "id" in item:
            refs.append(f"{item['type']}:{item['id']}")
    return refs


def check_refs(records: dict[str, Any], known_refs: set[str]) -> list[Finding]:
    """A ref not present in ``known_refs`` is an unresolved-reference blocker."""
    findings: list[Finding] = []
    for owner_ref, record in records.items():
        for ref in collect_refs(record):
            if ref not in known_refs:
                findings.append(
                    finding(
                        check_id=CHECK_ID,
                        severity="blocker",
                        reason=f"unresolved reference {ref!r}",
                        ref=owner_ref,
                        observed=ref,
                        proposed_action="Add the referenced artifact or fix the reference.",
                    )
                )
    return findings


@registry.register(id=CHECK_ID, version="1", scope="refs")
def _ref_check(ctx: ValidationContext) -> list[Finding]:
    return check_refs(ctx.records, ctx.known_refs)
