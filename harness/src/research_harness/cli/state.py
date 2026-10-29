"""`rh checkpoint`, `rh resume`, `rh history` handlers (02 §5.6, 03 §2.2)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from research_harness.core.envelope import build_envelope
from research_harness.core.errors import InvalidInputError
from research_harness.state.lock import holder_alive, read_lock, release
from research_harness.state.recovery import recover
from research_harness.state.store import Store


def resolve_object_root(explicit: str | None = None) -> Path:
    """Nearest directory (from ``explicit`` or cwd upward) that holds ``.rh/``."""
    start = Path(explicit) if explicit else Path.cwd()
    for d in [start, *start.parents]:
        if (d / ".rh").is_dir():
            return d
    raise InvalidInputError("error.no_object")


def checkpoint(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = resolve_object_root(getattr(args, "root", None))
    store = Store(root)
    result = store.checkpoint(
        by=args.by,
        request=args.request,
        units=args.units,
        note=args.message,
    )
    key = "checkpoint.reused" if result.reused else "checkpoint.created"
    env = build_envelope(
        command="checkpoint",
        status="ok",
        lang=lang,
        message_key=key,
        message_params={"snapshot": result.snapshot_id},
        operation_id=None,
        findings=result.findings,
        data={
            "snapshot_id": result.snapshot_id,
            "reused": result.reused,
            "unattributed_snapshot": result.unattributed_snapshot,
        },
    )
    return env, 0


def resume(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = resolve_object_root(getattr(args, "root", None))
    findings = recover(root, repair=True)
    # rh resume performs explicit stale-lock recovery after confirming the PID is gone.
    lock_path = root / ".rh" / "lock"
    info = read_lock(lock_path)
    if info is not None and not holder_alive(info):
        release(lock_path)
        findings.append(
            {
                "check_id": "state.stale_lock_removed",
                "severity": "info",
                "reason": f"removed stale lock from pid {info.pid}",
            }
        )
    env = build_envelope(
        command="resume",
        status="ok",
        lang=lang,
        message_key="resume.ok",
        findings=findings,
        data={"finding_count": len(findings)},
    )
    return env, 0


def history(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = resolve_object_root(getattr(args, "root", None))
    entries = Store(root).history()
    env = build_envelope(
        command="history",
        status="ok",
        lang=lang,
        message_key="history.ok",
        message_params={"n": len(entries)},
        data={"history": entries},
    )
    return env, 0
