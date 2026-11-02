"""Venue status check (integrity.md; M3-12, FR-37).

Records evidence of the target venue's indexing status on the date that matters.
No evidence → value ``unknown`` (D14). A ``not_included`` status blocks a verified
export (``integrity.venue_status``). Status is derived by the author/agent from
the resource; this module records and reports it — it never fabricates a status.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_harness.core.errors import InvalidInputError
from research_harness.schemas import validate
from research_harness.state.snapshot import atomic_write_bytes


def checks_dir(root: Path) -> Path:
    return root / "venue" / "checks"


def list_checks(root: Path) -> list[dict[str, Any]]:
    d = checks_dir(root)
    if not d.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for p in sorted(d.glob("VC-*.json")):
        out.append(json.loads(p.read_text(encoding="utf-8")))
    return out


def _next_id(root: Path) -> str:
    nums = [
        int(c["id"].split("-")[1]) for c in list_checks(root) if c.get("id", "").startswith("VC-")
    ]
    return f"VC-{max(nums, default=0) + 1:03d}"


def record_check(
    root: Path,
    *,
    title: str,
    resource: str,
    query_date: str,
    status_value: str,
    status_date: str,
    checked_by: str,
    issn: list[str] | None = None,
    evidence: dict[str, Any] | None = None,
    rule_refs: list[str] | None = None,
) -> dict[str, Any]:
    """Write one venue check to ``venue/checks/VC-NNN.json`` after validation."""
    rec: dict[str, Any] = {
        "id": _next_id(root),
        "venue": {"title": title},
        "resource": resource,
        "query_date": query_date,
        "status_on_date": {"date": status_date, "value": status_value},
        "evidence": evidence or {},
        "checked_by": checked_by,
    }
    if issn:
        rec["venue"]["issn"] = issn
    if rule_refs:
        rec["rule_refs"] = rule_refs
    errors = validate("venue-check", rec)
    if errors:
        raise InvalidInputError("error.venue_invalid")
    d = checks_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    body = json.dumps(rec, ensure_ascii=False, indent=2)
    atomic_write_bytes(d / f"{rec['id']}.json", (body + "\n").encode("utf-8"))
    return rec


def _latest(root: Path) -> dict[str, Any] | None:
    checks = list_checks(root)
    if not checks:
        return None
    return max(checks, key=lambda c: (c.get("query_date", ""), c.get("id", "")))


def status_findings(root: Path) -> list[dict[str, Any]]:
    """Report the current venue status for a verified export (FR-37)."""
    latest = _latest(root)
    if latest is None:
        return [_f("major", "no venue check recorded for the target venue", "unknown")]
    value = latest.get("status_on_date", {}).get("value")
    if value == "not_included":
        return [
            _f("blocker", f"venue {latest['venue']['title']} is not_included on the date", value)
        ]
    if value == "unknown":
        return [_f("major", f"venue status for {latest['venue']['title']} is unknown", value)]
    return []


def _f(severity: str, reason: str, observed: str) -> dict[str, Any]:
    return {
        "check_id": "integrity.venue_status",
        "severity": severity,
        "reason": reason,
        "location": {},
        "observed": observed,
        "proposed_action": "Record a venue check with dated evidence for the target venue.",
    }
