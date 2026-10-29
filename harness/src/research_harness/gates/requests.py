"""Approval requests bound to the current snapshot (02 §9.3)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_harness.core.errors import CorruptStateError
from research_harness.state import snapshot as snap
from research_harness.state.snapshot import atomic_write_bytes


def requests_dir(root: Path) -> Path:
    return root / "approvals" / "requests"


def _next_id(root: Path) -> str:
    d = requests_dir(root)
    n = len(list(d.glob("AR-*.json"))) + 1 if d.is_dir() else 1
    return f"AR-{n:04d}"


def current_target(root: Path, refs: list[str] | None = None) -> dict[str, Any]:
    cur = snap.read_current(root)
    if cur is None:
        raise CorruptStateError("error.corrupt")
    manifest = snap.load_snapshot(root, cur)
    return {"snapshot_id": cur, "manifest_sha256": manifest["manifest_sha256"], "refs": refs or []}


def open_request(
    root: Path, gate: str, *, briefing_text: str, summary_path: str, refs: list[str] | None = None
) -> str:
    """Create (or reuse an open) approval request for ``gate`` on the current snapshot."""
    d = requests_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    target = current_target(root, refs)

    # Reuse an open request for the same gate + snapshot (idempotent).
    for rf in sorted(d.glob("AR-*.json")):
        rec = json.loads(rf.read_text(encoding="utf-8"))
        if (
            rec["gate"] == gate
            and rec["status"] == "open"
            and rec["target"]["snapshot_id"] == target["snapshot_id"]
        ):
            return rec["id"]

    ar_id = _next_id(root)
    briefing_path = f"approvals/requests/{ar_id}.md"
    record = {
        "id": ar_id,
        "gate": gate,
        "target": target,
        "summary_path": summary_path,
        "briefing_path": briefing_path,
        "status": "open",
    }
    atomic_write_bytes(
        d / f"{ar_id}.json",
        (json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    )
    atomic_write_bytes(root / briefing_path, briefing_text.encode("utf-8"))
    return ar_id


def request_gate(root: Path, gate: str, lang: str, *, refs: list[str] | None = None) -> str:
    """Render the full briefing for ``gate`` and open (or reuse) its request."""
    from research_harness.gates.briefing import render

    summary_path = "intake/summary.md" if gate == "G0" else ""
    return open_request(
        root, gate, briefing_text=render(root, gate, lang), summary_path=summary_path, refs=refs
    )


def find_open_request(root: Path, gate: str) -> dict[str, Any] | None:
    for rec in open_requests(root, gate):
        return rec
    return None


def open_requests(root: Path, gate: str | None = None) -> list[dict[str, Any]]:
    d = requests_dir(root)
    if not d.is_dir():
        return []
    out = []
    for rf in sorted(d.glob("AR-*.json")):
        rec = json.loads(rf.read_text(encoding="utf-8"))
        if rec["status"] == "open" and (gate is None or rec["gate"] == gate):
            out.append(rec)
    return out
