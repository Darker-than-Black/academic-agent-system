"""Submission and publication records (lifecycle-records.md; M3-08, FR-28, T29a).

These describe external facts, so recording them is human-only (the CLI enforces
the TTY rule). A SubmissionRecord requires a valid G3 approval for the current
snapshot; recording tags that snapshot (``submitted:<date>`` / ``published``),
and tagged snapshots are frozen for migrations (NFR-10).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_harness.core.errors import BlockedError, InvalidInputError
from research_harness.core.hashing import canonical_json_hash
from research_harness.gates.records import approvals_path
from research_harness.schemas import validate
from research_harness.state.snapshot import atomic_write_bytes, load_snapshot, read_current

_APPROVE = {"approved", "approved_with_conditions"}


def _dir(root: Path, kind: str) -> Path:
    return root / "records" / kind


def tags_path(root: Path) -> Path:
    return root / "records" / "tags.json"


def load_tags(root: Path) -> dict[str, str]:
    p = tags_path(root)
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def _tag_snapshot(root: Path, tag: str, snapshot_id: str) -> None:
    tags = load_tags(root)
    tags[tag] = snapshot_id
    tags_path(root).parent.mkdir(parents=True, exist_ok=True)
    atomic_write_bytes(
        tags_path(root), (json.dumps(tags, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )


def _list(root: Path, kind: str, prefix: str) -> list[dict[str, Any]]:
    d = _dir(root, kind)
    if not d.is_dir():
        return []
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(d.glob(f"{prefix}-*.json"))]


def _next_id(root: Path, kind: str, prefix: str) -> str:
    nums = [int(r["id"].split("-")[1]) for r in _list(root, kind, prefix)]
    return f"{prefix}-{max(nums, default=0) + 1:02d}"


def _valid_g3(root: Path, snapshot_id: str) -> str | None:
    """Return the id of a valid G3 approval for ``snapshot_id`` (or None)."""
    p = approvals_path(root)
    if not p.is_file():
        return None
    best: str | None = None
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("gate") != "G3" or rec.get("decision") not in _APPROVE:
            continue
        target = rec.get("target", {})
        if target.get("snapshot_id") in (None, snapshot_id):
            best = rec.get("id")
    return best


def _snapshot_or_block(root: Path) -> str:
    sid = read_current(root)
    if not sid:
        raise BlockedError("error.no_snapshot")
    return sid


def _write(root: Path, kind: str, rec: dict[str, Any], schema: str) -> dict[str, Any]:
    if validate(schema, rec):
        raise InvalidInputError(f"error.{schema.replace('-', '_')}_invalid")
    d = _dir(root, kind)
    d.mkdir(parents=True, exist_ok=True)
    body = json.dumps(rec, ensure_ascii=False, indent=2)
    atomic_write_bytes(d / f"{rec['id']}.json", (body + "\n").encode("utf-8"))
    return rec


def record_submission(
    root: Path,
    *,
    venue_title: str,
    date: str,
    channel_note: str,
    issn: list[str] | None = None,
    manuscript_id: str | None = None,
) -> dict[str, Any]:
    """Record a submission (requires a valid G3 for the current snapshot)."""
    snapshot_id = _snapshot_or_block(root)
    g3 = _valid_g3(root, snapshot_id)
    if not g3:
        raise BlockedError("error.no_valid_g3")
    rec: dict[str, Any] = {
        "id": _next_id(root, "submissions", "SUB"),
        "venue": {"title": venue_title},
        "date": date,
        "snapshot_id": snapshot_id,
        "manifest_sha256": canonical_json_hash(load_snapshot(root, snapshot_id)),
        "g3_approval_id": g3,
        "channel_note": channel_note,
    }
    if issn:
        rec["venue"]["issn"] = issn
    if manuscript_id:
        rec["manuscript_id"] = manuscript_id
    out = _write(root, "submissions", rec, "submission-record")
    _tag_snapshot(root, f"submitted:{date}", snapshot_id)
    return out


def record_publication(
    root: Path,
    *,
    submission_id: str,
    date: str,
    doi: str | None = None,
    volume: str | None = None,
    issue: str | None = None,
    pages: str | None = None,
    license: str | None = None,
    url: str | None = None,
) -> dict[str, Any]:
    """Record a publication (version of record = current snapshot)."""
    snapshot_id = _snapshot_or_block(root)
    rec: dict[str, Any] = {
        "id": _next_id(root, "publications", "PUB"),
        "submission_id": submission_id,
        "date": date,
        "snapshot_id": snapshot_id,
    }
    for k, v in (
        ("doi", doi),
        ("volume", volume),
        ("issue", issue),
        ("pages", pages),
        ("license", license),
        ("url", url),
    ):
        if v:
            rec[k] = v
    out = _write(root, "publications", rec, "publication-record")
    _tag_snapshot(root, "published", snapshot_id)
    return out
