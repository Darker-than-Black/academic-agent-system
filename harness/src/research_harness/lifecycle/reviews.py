"""Reviewer comments (lifecycle-records.md; M3-08, FR-41, T44).

Mode ``respond_to_reviewers`` (A14): each reviewer comment is recorded, then
closed with an action (accept / partial / decline), a response and the units it
changed, or argued. Deterministic record-keeping; the argument text is the
author's.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_harness.core.errors import InvalidInputError
from research_harness.schemas import validate
from research_harness.state.snapshot import atomic_write_bytes


def _dir(root: Path) -> Path:
    return root / "reviews" / "comments"


def list_comments(root: Path) -> list[dict[str, Any]]:
    d = _dir(root)
    if not d.is_dir():
        return []
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(d.glob("RC-*.json"))]


def _next_id(root: Path) -> str:
    nums = [int(c["id"].split("-")[1]) for c in list_comments(root)]
    return f"RC-{max(nums, default=0) + 1:02d}"


def _save(root: Path, rec: dict[str, Any]) -> dict[str, Any]:
    if validate("reviewer-comment", rec):
        raise InvalidInputError("error.reviewer_comment_invalid")
    d = _dir(root)
    d.mkdir(parents=True, exist_ok=True)
    body = json.dumps(rec, ensure_ascii=False, indent=2)
    atomic_write_bytes(d / f"{rec['id']}.json", (body + "\n").encode("utf-8"))
    return rec


def add_comment(
    root: Path, *, round: int, reviewer: str, text: str, location_hint: str | None = None
) -> dict[str, Any]:
    rec: dict[str, Any] = {
        "id": _next_id(root),
        "round": round,
        "reviewer": reviewer,
        "text": text,
        "status": "open",
    }
    if location_hint:
        rec["location_hint"] = location_hint
    return _save(root, rec)


def _load_one(root: Path, rc_id: str) -> dict[str, Any]:
    p = _dir(root) / f"{rc_id}.json"
    if not p.is_file():
        raise InvalidInputError("error.reviewer_comment_unknown")
    return json.loads(p.read_text(encoding="utf-8"))


def respond(
    root: Path,
    rc_id: str,
    *,
    action: str,
    response: str,
    changed_units: list[str] | None = None,
    evidence_refs: list[str] | None = None,
) -> dict[str, Any]:
    """Close a comment with an action, a response and the units it changed."""
    rec = _load_one(root, rc_id)
    rec["action"] = action
    rec["response"] = response
    rec["changed_units"] = changed_units or []
    rec["evidence_refs"] = evidence_refs or []
    rec["status"] = "closed"
    return _save(root, rec)


def open_count(root: Path) -> int:
    return sum(1 for c in list_comments(root) if c.get("status") == "open")
