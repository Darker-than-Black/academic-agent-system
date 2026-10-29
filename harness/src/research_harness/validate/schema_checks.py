"""Schema-scope checks: records must satisfy their JSON Schema (02 §14)."""

from __future__ import annotations

from typing import Any

from research_harness import schemas
from research_harness.validate.framework import (
    Finding,
    ValidationContext,
    finding,
    registry,
)

CHECK_ID = "schema.record_valid"


def validate_record(schema_name: str, record: Any, ref: str | None = None) -> list[Finding]:
    """Validate one record against ``schema_name``; a violation is a blocker."""
    findings: list[Finding] = []
    for message in schemas.validate(schema_name, record):
        findings.append(
            finding(
                check_id=CHECK_ID,
                severity="blocker",
                reason=f"{schema_name}: {message}",
                ref=ref,
                proposed_action="Fix the record to match its schema.",
            )
        )
    return findings


@registry.register(id=CHECK_ID, version="1", scope="schema")
def _schema_check(ctx: ValidationContext) -> list[Finding]:
    findings: list[Finding] = []
    for item in ctx.extra.get("records_to_validate", []):
        findings.extend(validate_record(item["schema"], item["record"], item.get("ref")))
    return findings
