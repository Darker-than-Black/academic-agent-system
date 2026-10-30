"""Counter-evidence records (``lab/counter-evidence.jsonl``): for every central
claim, the queries run and the outcome. ``not_found_after_search`` requires at
least one logged query — absence of a search is never evidence of absence (FR-29).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_harness.core.clock import default_clock
from research_harness.core.ulid import new_ulid

OUTCOMES = ("found", "not_found_after_search", "inconclusive")


def counter_path(root: Path) -> Path:
    return root / "lab" / "counter-evidence.jsonl"


def load_records(root: Path) -> list[dict[str, Any]]:
    path = counter_path(root)
    if not path.is_file():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def record(
    root: Path,
    *,
    claim_ref: str,
    queries: list[str],
    outcome: str,
    note: str | None = None,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    queries = [q for q in (queries or []) if q.strip()]
    if outcome == "not_found_after_search" and not queries:
        finding = {
            "check_id": "counter.no_query",
            "severity": "blocker",
            "reason": f"{claim_ref}: 'not_found_after_search' needs at least one logged query",
            "location": {"ref": claim_ref},
            "proposed_action": "",
        }
        return None, [finding]

    entry = {
        "id": "ce-" + new_ulid(),
        "at": default_clock().now_rfc3339(),
        "claim_ref": claim_ref,
        "queries": queries,
        "outcome": outcome,
    }
    if note:
        entry["note"] = note
    path = counter_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry, []


def covered_claims(root: Path) -> set[str]:
    return {r["claim_ref"] for r in load_records(root)}
