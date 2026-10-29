"""`rh validate --scope …` handler (read-only; 03 §2, 02 §9.4).

M1-03 wires schema and ref checks and supports validating explicit files
(`--schema NAME --file PATH`). Object-wide validation against the current
snapshot is added when state lands (M1-04/M1-11); those cards register more
checks (freshness, structure) with the same framework.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from research_harness.core.envelope import build_envelope

# ref_checks / schema_checks are imported for their check-registration side effect.
from research_harness.validate import (
    has_blocker,
    ref_checks,  # noqa: F401
    registry,
    run_checks,
    schema_checks,  # noqa: F401
)
from research_harness.validate.framework import ValidationContext

VALID_SCOPES = {"schema", "refs", "structure", "freshness", "all"}


def _load(path: str) -> Any:
    text = Path(path).read_text(encoding="utf-8")
    if path.endswith((".yaml", ".yml")):
        return yaml.safe_load(text)
    return json.loads(text)


def run(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    scope = args.scope or "all"
    ctx = ValidationContext()
    if getattr(args, "known", None):
        ctx.known_refs = set(args.known)
    if getattr(args, "schema", None) and getattr(args, "file", None):
        ctx.extra["records_to_validate"] = [
            {"schema": args.schema, "ref": f"file:{p}", "record": _load(p)} for p in args.file
        ]
        for item in ctx.extra["records_to_validate"]:
            ctx.records[item["ref"]] = item["record"]

    findings = run_checks([scope], ctx)
    blocked = has_blocker(findings)
    envelope = build_envelope(
        command="validate",
        status="blocked" if blocked else "ok",
        lang=lang,
        message_key="validate.blocked" if blocked else "validate.ok",
        message_params={"n": len(findings)},
        findings=findings,
        data={
            "scope": scope,
            "finding_count": len(findings),
            "scopes_available": sorted(registry.scopes()),
        },
    )
    return envelope, (3 if blocked else 0)
