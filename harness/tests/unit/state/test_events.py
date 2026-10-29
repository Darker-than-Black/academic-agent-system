"""Event log tests (02 §5.1, §5.5)."""

from __future__ import annotations

from pathlib import Path

from research_harness.state.events import append_event, make_event, read_events


def test_append_and_read(tmp_path: Path) -> None:
    ep = tmp_path / "events.jsonl"
    append_event(ep, make_event("commit", snapshot_id="snap-x"))
    append_event(ep, make_event("commit", snapshot_id="snap-y"))
    events, truncated = read_events(ep)
    assert truncated is None
    assert [e["snapshot_id"] for e in events] == ["snap-x", "snap-y"]


def test_truncated_tail_detected(tmp_path: Path) -> None:
    ep = tmp_path / "events.jsonl"
    append_event(ep, make_event("commit", snapshot_id="snap-x"))
    with open(ep, "a", encoding="utf-8") as fh:
        fh.write('{"id": "ev-partial", "at":')  # interrupted append, no newline
    events, truncated = read_events(ep)
    assert len(events) == 1
    assert truncated is not None and "ev-partial" in truncated


def test_missing_file(tmp_path: Path) -> None:
    events, truncated = read_events(tmp_path / "nope.jsonl")
    assert events == [] and truncated is None
