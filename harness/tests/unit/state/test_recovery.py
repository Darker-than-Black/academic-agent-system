"""Recovery tests (02 §5.5)."""

from __future__ import annotations

from pathlib import Path

import pytest

from research_harness.core.errors import CorruptStateError
from research_harness.state import snapshot as snap
from research_harness.state.recovery import recover
from research_harness.state.store import Store

HUMAN = {"kind": "human", "name": "t", "version": "0.1.0"}


def mkroot(tmp_path: Path) -> Store:
    (tmp_path / "object.json").write_text('{"x": 1}\n', encoding="utf-8")
    store = Store(tmp_path)
    store.init(HUMAN)
    return store


def test_roll_forward_when_current_older(tmp_path: Path) -> None:
    store = mkroot(tmp_path)
    first = snap.read_current(tmp_path)
    (tmp_path / "object.json").write_text('{"x": 2}\n', encoding="utf-8")
    result = store.checkpoint(by="human")
    newest = result.snapshot_id
    # Simulate a crash right before CURRENT was updated.
    snap.write_current(tmp_path, first)
    findings = recover(tmp_path, repair=True)
    assert snap.read_current(tmp_path) == newest
    assert any(f["check_id"] == "state.rolled_forward" for f in findings)


def test_truncated_events_quarantined(tmp_path: Path) -> None:
    mkroot(tmp_path)
    ep = tmp_path / ".rh" / "events.jsonl"
    with open(ep, "a", encoding="utf-8") as fh:
        fh.write('{"partial":')
    findings = recover(tmp_path, repair=True)
    assert any(f["check_id"] == "state.events_truncated" for f in findings)
    quarantine = list((tmp_path / ".rh" / "quarantine").glob("events.corrupt-*.jsonl"))
    assert quarantine
    # events.jsonl now parses cleanly
    from research_harness.state.events import read_events

    _events, truncated = read_events(ep)
    assert truncated is None


def test_missing_blob_is_corrupt(tmp_path: Path) -> None:
    mkroot(tmp_path)
    cur = snap.read_current(tmp_path)
    manifest = snap.load_snapshot(tmp_path, cur)
    sha = next(e["sha256"] for e in manifest["files"] if e["stored"])
    snap.blob_path(tmp_path, sha).unlink()
    with pytest.raises(CorruptStateError) as exc:
        recover(tmp_path, repair=True)
    assert exc.value.exit_code == 5


def test_recover_clean_tree_noop(tmp_path: Path) -> None:
    mkroot(tmp_path)
    assert recover(tmp_path, repair=True) == []
