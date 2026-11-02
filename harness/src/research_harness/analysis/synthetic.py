"""Synthetic-participant guard (M3-21, FR-59, T65).

Model-generated respondents or interviews are not data: only ``simulated`` runs
with ``purpose: instrument_pilot`` are allowed, and any claim whose evidence
includes a row from such a run is blocked (``analysis.simulated_as_evidence``).
``simulated`` never supports a claim (invariant 4). Deterministic; no LLM."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_harness.analysis import rows as rows_mod
from research_harness.analysis import runner


def _run_origin(root: Path, run_id: str) -> str | None:
    path = runner.runs_dir(root) / run_id / "run.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("origin")
    except json.JSONDecodeError:
        return None


def simulated_runs(root: Path) -> set[str]:
    d = runner.runs_dir(root)
    if not d.is_dir():
        return set()
    return {p.name for p in d.glob("R-*") if _run_origin(root, p.name) == "simulated"}


def claim_row_refs(claim: dict[str, Any]) -> list[str]:
    """Every result-row id a claim leans on: its result_ref and result_row evidence."""
    refs: list[str] = []
    if claim.get("result_ref"):
        refs.append(claim["result_ref"])
    for ev in claim.get("evidence", []):
        if ev.get("type") == "result_row" and ev.get("id"):
            refs.append(ev["id"])
    return refs


def findings(root: Path) -> list[dict[str, Any]]:
    """``analysis.simulated_as_evidence`` blocker for any claim relying on a row
    produced by a simulated run."""
    simulated = simulated_runs(root)
    if not simulated:
        return []
    rows_by_id = rows_mod.by_id(root)
    out: list[dict[str, Any]] = []
    man = root / "manuscript"
    if not man.is_dir():
        return out
    for cf in man.rglob("claims.json"):
        data = json.loads(cf.read_text(encoding="utf-8"))
        for claim in data if isinstance(data, list) else data.get("claims", []):
            bad = sorted(
                {
                    rid
                    for rid in claim_row_refs(claim)
                    if (rows_by_id.get(rid) or {}).get("run_id") in simulated
                }
            )
            if bad:
                out.append(
                    {
                        "check_id": "analysis.simulated_as_evidence",
                        "severity": "blocker",
                        "reason": (
                            f"claim {claim.get('id', '?')} cites simulated rows "
                            f"({', '.join(bad)}); simulated data never supports a claim"
                        ),
                        "location": {"claim": claim.get("id")},
                        "observed": bad,
                        "proposed_action": "Base the claim on real data, not an instrument pilot.",
                    }
                )
    return out
