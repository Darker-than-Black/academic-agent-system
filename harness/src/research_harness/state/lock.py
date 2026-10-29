"""Single-writer lock (02 §5.4).

``.rh/lock`` is created with ``O_CREAT | O_EXCL`` and holds the holder metadata.
A second writer gets exit 4. A lock whose process is gone is never removed
silently: commands report it and ``rh resume`` recovers it explicitly.
"""

from __future__ import annotations

import json
import os
import socket
from dataclasses import asdict, dataclass
from pathlib import Path

from research_harness.core.clock import default_clock
from research_harness.core.errors import ToolFailureError


@dataclass(frozen=True)
class LockInfo:
    operation_id: str
    pid: int
    hostname: str
    command: str
    started_at: str


class LockHeld(ToolFailureError):
    """Raised (exit 4) when the lock is already held by another writer."""

    def __init__(self, holder: LockInfo | None) -> None:
        super().__init__("error.lock_held")
        self.holder = holder


def read_lock(lock_path: Path) -> LockInfo | None:
    try:
        data = json.loads(lock_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    try:
        return LockInfo(**data)
    except TypeError:
        return None


def acquire(lock_path: Path, operation_id: str, command: str) -> LockInfo:
    """Create the lock exclusively; raise :class:`LockHeld` if it already exists."""
    info = LockInfo(
        operation_id=operation_id,
        pid=os.getpid(),
        hostname=socket.gethostname(),
        command=command,
        started_at=default_clock().now_rfc3339(),
    )
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        raise LockHeld(read_lock(lock_path)) from None
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(asdict(info), fh)
        fh.flush()
        os.fsync(fh.fileno())
    return info


def release(lock_path: Path) -> None:
    lock_path.unlink(missing_ok=True)


def holder_alive(info: LockInfo) -> bool:
    """True if the lock holder's PID is still running on this host."""
    if info.hostname != socket.gethostname():
        return True  # cannot tell about another host; treat as alive
    try:
        os.kill(info.pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True
