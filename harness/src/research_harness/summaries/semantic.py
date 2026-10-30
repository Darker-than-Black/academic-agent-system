"""Semantic summary part (stored, produced by the summarizer role; the critic
checks faithfulness in M3). At most 150 words of prose plus claim IDs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from research_harness.structure import ops
from research_harness.summaries.deterministic import _claims, _write, load_summary

MAX_WORDS = 150


def set_semantic(
    root: Path,
    unit_id: str,
    *,
    main_thesis: str,
    key_claims: list[str],
    open_questions: list[str] | None = None,
    language: str = "uk",
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    folder = ops.current_folders(root)[unit_id]
    summary = load_summary(folder)
    findings: list[dict[str, Any]] = []
    if not summary:
        findings.append(
            {
                "check_id": "summary.semantic_missing",
                "severity": "major",
                "reason": f"{unit_id}: build the deterministic summary before the semantic part",
                "location": {},
                "proposed_action": "",
            }
        )
        return {}, findings

    if len(main_thesis.split()) > MAX_WORDS:
        findings.append(
            {
                "check_id": "summary.too_long",
                "severity": "major",
                "reason": f"{unit_id}: semantic summary exceeds {MAX_WORDS} words",
                "location": {},
                "proposed_action": "",
            }
        )
    known_claims = set(_claims(folder))
    for cid in key_claims:
        if cid not in known_claims:
            findings.append(
                {
                    "check_id": "summary.unknown_claim",
                    "severity": "major",
                    "reason": f"{unit_id}: key claim {cid!r} is not a claim of this unit",
                    "location": {},
                    "proposed_action": "",
                }
            )
    if any(f["severity"] in ("blocker", "major") for f in findings):
        return summary, findings

    summary["semantic"] = {
        "main_thesis": main_thesis,
        "key_claims": key_claims,
        "open_questions": open_questions or [],
        "language": language,
    }
    _write(folder, summary)  # re-validates against the schema
    return summary, findings
