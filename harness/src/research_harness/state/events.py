"""Append-only diagnostic event log (02 §5.1, §5.5).

Snapshots are authoritative; events are diagnostic. A truncated final line (an
interrupted append) is isolated to quarantine and reported, never hidden.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from research_harness.core.clock import default_clock
from research_harness.core.ids import new_event_id


def append_event(events_path: Path, event: dict[str, Any]) -> None:
    """Append one JSON line and fsync the file."""
    events_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(event, ensure_ascii=False, sort_keys=True)
    with open(events_path, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def make_event(type_: str, **data: Any) -> dict[str, Any]:
    event: dict[str, Any] = {
        "id": new_event_id(),
        "at": default_clock().now_rfc3339(),
        "type": type_,
    }
    event.update(data)
    return event


def read_events(events_path: Path) -> tuple[list[dict[str, Any]], str | None]:
    """Return (events, truncated_tail). The tail is the raw last line if it is
    not valid JSON (an interrupted append), else ``None``."""
    if not events_path.exists():
        return [], None
    lines = events_path.read_text(encoding="utf-8").splitlines()
    events: list[dict[str, Any]] = []
    truncated: str | None = None
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            # Only a truncated *final* line is tolerated; anything earlier is
            # still surfaced as a truncated tail starting here.
            truncated = "\n".join(lines[i:])
            break
    return events, truncated
