"""Search log (``lab/search-log.jsonl``): one line per query, incl. manual
exports; plus run (API adapters), coverage and stop recording.

No search without a stored plan (invariant 1). "Not checked" ≠ "nothing found":
an unavailable or unrun resource is a coverage gap, never zero results.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_harness.core.clock import default_clock
from research_harness.core.errors import BlockedError
from research_harness.core.hashing import file_hash
from research_harness.core.ulid import new_ulid
from research_harness.lab import plan as plan_mod
from research_harness.schemas import validate
from research_harness.sources import registry
from research_harness.sources.adapters import get_adapter
from research_harness.sources.policy import is_api, is_deferred
from research_harness.sources.policy import resources as policy_resources
from research_harness.sources.transport import Transport


def log_path(root: Path) -> Path:
    return root / "lab" / "search-log.jsonl"


def stops_path(root: Path) -> Path:
    return root / "lab" / "stops.jsonl"


def _require_plan(root: Path) -> int:
    if not plan_mod.has_plan(root):
        raise BlockedError("error.search_no_plan")
    return plan_mod.latest_version(root)


def _append(root: Path, line: dict[str, Any]) -> dict[str, Any]:
    errors = validate("search-log", line)
    if errors:
        raise ValueError(f"invalid search-log line: {errors}")
    path = log_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(line, ensure_ascii=False) + "\n")
    return line


def load_log(root: Path) -> list[dict[str, Any]]:
    path = log_path(root)
    if not path.is_file():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def run_search(
    root: Path, adapter: str, query: str, *, transport: Transport | None = None
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Run an API search, append a log line, add candidates to the registry."""
    plan_version = _require_plan(root)
    if not is_api(adapter) or is_deferred(adapter):
        line = _append(
            root,
            {
                "id": "sl-" + new_ulid(),
                "at": default_clock().now_rfc3339(),
                "resource": adapter,
                "mode": "api",
                "query": query,
                "status": "unavailable",
                "records_returned": 0,
                "plan_version": plan_version,
            },
        )
        return line, []

    ad = get_adapter(adapter, transport=transport)
    if adapter == "crossref":
        res = ad.search_by_title(query)
    elif hasattr(ad, "search"):
        res = ad.search(query)
    else:
        res = ad.lookup_by_doi(query)

    added: list[dict[str, Any]] = []
    if res.status == "ok" and res.records:
        added, _ = registry.add_records(root, res.records)
    line = _append(
        root,
        {
            "id": "sl-" + new_ulid(),
            "at": res.retrieved_at,
            "resource": adapter,
            "mode": "api",
            "query": query,
            "status": res.status,
            "records_returned": len(res.records),
            "plan_version": plan_version,
        },
    )
    return line, added


def manual_log(
    root: Path,
    resource: str,
    query: str,
    results: int,
    *,
    export_file: Path | None = None,
    mode: str = "manual_export",
) -> dict[str, Any]:
    """Record a manual search / export (Scopus, WoS, Scholar, НБУВ)."""
    plan_version = _require_plan(root)
    line: dict[str, Any] = {
        "id": "sl-" + new_ulid(),
        "at": default_clock().now_rfc3339(),
        "resource": resource,
        "mode": mode,
        "query": query,
        "status": "ok",
        "results_total": results,
        "records_returned": results,
        "plan_version": plan_version,
    }
    if export_file is not None:
        line["export_file_sha256"] = file_hash(export_file)
    return _append(root, line)


def coverage(root: Path) -> list[dict[str, Any]]:
    """Per-resource search coverage: ok / unavailable / not_checked (FR-20)."""
    log = load_log(root)
    best: dict[str, str] = {}
    for line in log:
        res, status = line["resource"], line["status"]
        if res not in best or status == "ok":
            best[res] = status
    out = []
    for name in policy_resources():
        out.append({"resource": name, "status": best.get(name, "not_checked")})
    return out


def record_stop(root: Path, reason: str, uncovered: list[str] | None = None) -> dict[str, Any]:
    """Record a search stop with its reason and what remains uncovered (T61)."""
    entry = {
        "id": "stop-" + new_ulid(),
        "at": default_clock().now_rfc3339(),
        "reason": reason,
        "uncovered": uncovered or [],
    }
    path = stops_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry
