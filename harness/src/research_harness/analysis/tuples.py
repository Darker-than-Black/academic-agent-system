"""Tuple validators for own numeric claims (M3-19, ADR-009, FR-06).

An ``own_numeric`` claim is supported only if its ``result_ref`` resolves to a
current result row, every ``expected_tuple`` field equals the row's, the units
match (``%`` ≠ ``p.p.``), and the shown number equals the row value after the
*declared* transformation — no implicit ×100/÷100 and no undeclared tolerance.
These catch the N2 / F8 defects (95 s vs 95 %, 0.125 shown as 12.5 %, a number
from another subsample, unweighted vs weighted). Deterministic; no LLM.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_harness.analysis import rows as rows_mod

# expected_tuple field -> result row field.
_TUPLE_MAP = {
    "dataset_id": "dataset_id",
    "split_id": "subset",
    "condition": "condition",
    "metric_id": "variable_or_metric",
    "aggregation": "aggregation",
}


def _f(check_id: str, severity: str, claim_id: str, reason: str, observed: Any = None) -> dict:
    return {
        "check_id": check_id,
        "severity": severity,
        "reason": reason,
        "location": {"claim": claim_id},
        "observed": observed,
        "proposed_action": "Point the claim at the correct result row, or fix the number/unit.",
    }


def _looks_like_scale_100(shown: float, row_value: float) -> bool:
    if row_value == 0:
        return False
    ratio = shown / row_value
    return abs(ratio - 100) < 1e-9 or abs(ratio - 0.01) < 1e-9


def check_claim(claim: dict[str, Any], rows_by_id: dict[str, dict[str, Any]]) -> list[dict]:
    if claim.get("kind") != "own_numeric":
        return []
    cid = claim.get("id", "?")
    rr = claim.get("result_ref")
    et = claim.get("expected_tuple", {})
    row = rows_by_id.get(rr) if rr else None
    if row is None:
        return [
            _f(
                "analysis.tuple_mismatch",
                "blocker",
                cid,
                f"result_ref {rr!r} does not resolve to a current result row",
                observed=rr,
            )
        ]

    findings: list[dict] = []
    mismatched = [
        tf for tf, rf in _TUPLE_MAP.items() if str(et.get(tf, "")) != str(row.get(rf, ""))
    ]
    if mismatched:
        findings.append(
            _f(
                "analysis.tuple_mismatch",
                "blocker",
                cid,
                f"expected_tuple differs from row {row['id']} on: {', '.join(mismatched)}",
                observed={tf: [et.get(tf), row.get(_TUPLE_MAP[tf])] for tf in mismatched},
            )
        )
    if str(et.get("unit", "")) != str(row.get("unit", "")):
        findings.append(
            _f(
                "analysis.unit_mismatch",
                "blocker",
                cid,
                f"unit {et.get('unit')!r} != row unit {row.get('unit')!r} (e.g. % vs p.p.)",
                observed=[et.get("unit"), row.get("unit")],
            )
        )

    if "shown_value" in claim:
        findings += _check_value(claim, row, cid)
    return findings


def _check_value(claim: dict[str, Any], row: dict[str, Any], cid: str) -> list[dict]:
    shown = claim["shown_value"]
    row_value = row.get("value")
    transform = claim.get("transform") or {}
    factor = transform.get("factor")
    if not isinstance(shown, (int, float)) or not isinstance(row_value, (int, float)):
        if shown != row_value:
            return [_f("analysis.tuple_mismatch", "blocker", cid, "shown value != row value")]
        return []
    expected = row_value * factor if factor is not None else row_value
    if shown == expected:
        return []
    if factor is None and _looks_like_scale_100(shown, row_value):
        return [
            _f(
                "analysis.implicit_conversion",
                "blocker",
                cid,
                f"shown {shown} is an undeclared ×100/÷100 of row value {row_value}",
                observed=[shown, row_value],
            )
        ]
    return [
        _f(
            "analysis.tuple_mismatch",
            "blocker",
            cid,
            f"shown {shown} != row value {row_value} after declared transform",
            observed=[shown, expected],
        )
    ]


def check(root: Path) -> list[dict]:
    """Run the tuple validators over every own_numeric claim in the object."""
    rows_by_id = rows_mod.by_id(root)
    findings: list[dict] = []
    man = root / "manuscript"
    if not man.is_dir():
        return findings
    for cf in man.rglob("claims.json"):
        data = json.loads(cf.read_text(encoding="utf-8"))
        claims = data if isinstance(data, list) else data.get("claims", [])
        for claim in claims:
            findings += check_claim(claim, rows_by_id)
    return findings
