"""Recovery at command start (02 §5.5).

Read-only commands report; mutating commands repair. Returns a list of finding
dicts; a missing blob for the current snapshot raises CorruptStateError (exit 5).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from research_harness.core.clock import default_clock
from research_harness.core.errors import CorruptStateError
from research_harness.state import snapshot as snap
from research_harness.state.events import append_event, make_event, read_events
from research_harness.state.lock import holder_alive, read_lock


def _finding(check_id: str, severity: str, reason: str) -> dict[str, Any]:
    return {"check_id": check_id, "severity": severity, "reason": reason}


def _events_path(root: Path) -> Path:
    return root / ".rh" / "events.jsonl"


def recover(root: Path, *, repair: bool) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    rhd = root / ".rh"
    if not rhd.is_dir():
        return findings

    # 0. Stale lock: report, never remove silently (rh resume removes it).
    lock_info = read_lock(rhd / "lock")
    if lock_info is not None and not holder_alive(lock_info):
        findings.append(
            _finding(
                "state.stale_lock", "minor", f"stale lock from pid {lock_info.pid} (process gone)"
            )
        )

    cur = snap.read_current(root)
    snaps = snap.all_snapshots(root)

    # 1. Snapshot committed but CURRENT still older → roll forward.
    children = [s for s in snaps if s.get("parent") == cur and s["id"] != cur]
    if children:
        target = sorted(children, key=lambda s: (s["created_at"], s["id"]))[-1]
        if repair:
            if snap.missing_blobs(root, target):
                raise CorruptStateError("error.corrupt")
            snap.materialize(root, target)
            snap.write_current(root, target["id"])
            append_event(
                _events_path(root),
                make_event(
                    "recovered", snapshot_id=target["id"], recovered=True, kind="roll_forward"
                ),
            )
            cur = target["id"]
            findings.append(
                _finding("state.rolled_forward", "info", f"rolled forward to {target['id']}")
            )
        else:
            findings.append(
                _finding(
                    "state.snapshot_uncommitted",
                    "info",
                    "a committed snapshot is newer than CURRENT",
                )
            )

    # 1b. Interrupted two-phase structure rename (02 §7.3).
    if repair and (rhd / "structure-journal.json").exists():
        from research_harness.structure.ops import complete_journal

        if complete_journal(root):
            findings.append(
                _finding(
                    "state.structure_rename_completed", "minor", "finished an interrupted rename"
                )
            )

    # 2. Orphaned staging directories.
    staging = rhd / "staging"
    if staging.is_dir():
        for child in sorted(staging.iterdir()):
            if not child.is_dir():
                continue
            if repair:
                dest = rhd / "quarantine" / f"staging-{child.name}"
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(child), str(dest))
                findings.append(
                    _finding(
                        "state.staging_quarantined", "minor", f"quarantined staging {child.name}"
                    )
                )
            else:
                findings.append(
                    _finding("state.staging_orphan", "minor", f"orphan staging {child.name}")
                )

    # 3. Truncated events tail.
    events, truncated = read_events(_events_path(root))
    if truncated is not None:
        if repair:
            ts = default_clock().now_rfc3339().replace(":", "")
            q = rhd / "quarantine" / f"events.corrupt-{ts}.jsonl"
            q.parent.mkdir(parents=True, exist_ok=True)
            q.write_text(truncated, encoding="utf-8")
            good = "".join(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n" for e in events)
            (_events_path(root)).write_text(good, encoding="utf-8")
        findings.append(
            _finding("state.events_truncated", "minor", "events.jsonl had a truncated tail")
        )

    # 4. CURRENT updated but no event recorded for it.
    if cur is not None and repair:
        events, _ = read_events(_events_path(root))
        if not any(e.get("snapshot_id") == cur for e in events):
            append_event(
                _events_path(root),
                make_event(
                    "recovered", snapshot_id=cur, recovered=True, kind="event_reconstructed"
                ),
            )
            findings.append(
                _finding("state.event_reconstructed", "info", f"reconstructed event for {cur}")
            )

    # 5. Missing blob for the current snapshot → corrupt.
    if cur is not None:
        manifest = snap.load_snapshot(root, cur)
        if snap.missing_blobs(root, manifest):
            raise CorruptStateError("error.corrupt")

    return findings
