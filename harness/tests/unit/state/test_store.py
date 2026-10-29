"""Store / commit protocol tests (02 §5.3–§5.6)."""

from __future__ import annotations

from pathlib import Path

import pytest

from research_harness.core.errors import BlockedError, InvalidInputError, ToolFailureError
from research_harness.state import snapshot as snap
from research_harness.state.dirty import dirty_set
from research_harness.state.lock import acquire
from research_harness.state.store import Store

HUMAN = {"kind": "human", "name": "t", "version": "0.1.0"}


def mkroot(tmp_path: Path) -> Store:
    (tmp_path / "object.json").write_text('{"x": 1}\n', encoding="utf-8")
    store = Store(tmp_path)
    store.init(HUMAN)
    return store


def test_init_creates_current_and_snapshot(tmp_path: Path) -> None:
    store = mkroot(tmp_path)
    assert snap.read_current(tmp_path) is not None
    assert len(store.history()) == 1


def test_author_edit_then_checkpoint(tmp_path: Path) -> None:
    store = mkroot(tmp_path)
    (tmp_path / "object.json").write_text('{"x": 2}\n', encoding="utf-8")
    assert dirty_set(tmp_path) == {"object.json"}
    result = store.checkpoint(by="human")
    assert not result.reused
    assert len(store.history()) == 2
    assert dirty_set(tmp_path) == set()  # tree equals CURRENT after checkpoint


def test_checkpoint_agent_requires_request(tmp_path: Path) -> None:
    store = mkroot(tmp_path)
    (tmp_path / "object.json").write_text('{"x": 9}\n', encoding="utf-8")
    with pytest.raises(InvalidInputError):
        store.checkpoint(by="agent")


def test_checkpoint_agent_request_in_history(tmp_path: Path) -> None:
    store = mkroot(tmp_path)
    (tmp_path / "object.json").write_text('{"x": 3}\n', encoding="utf-8")
    store.checkpoint(by="agent", request="скороти вступ")
    last = store.history()[-1]
    assert last["request"] == "скороти вступ"
    assert last["producer"]["kind"] == "model"


def test_idempotent_checkpoint_no_change(tmp_path: Path) -> None:
    store = mkroot(tmp_path)
    (tmp_path / "object.json").write_text('{"x": 4}\n', encoding="utf-8")
    first = store.checkpoint(by="human")
    second = store.checkpoint(by="human")  # nothing changed
    assert second.reused
    assert second.snapshot_id == first.snapshot_id
    assert len(store.history()) == 2


def test_staged_commit_materializes(tmp_path: Path) -> None:
    store = mkroot(tmp_path)
    result = store.commit(
        command="testop",
        args={"k": 1},
        producer=HUMAN,
        staged={"manuscript/01/text.md": b"hello\n"},
        write_set={"manuscript/01/text.md"},
    )
    assert not result.reused
    assert (tmp_path / "manuscript/01/text.md").read_bytes() == b"hello\n"


def test_dirty_outside_write_set_recorded_unattributed(tmp_path: Path) -> None:
    store = mkroot(tmp_path)
    # author edit outside the operation's write set
    (tmp_path / "object.json").write_text('{"x": 7}\n', encoding="utf-8")
    result = store.commit(
        command="testop",
        args={},
        producer=HUMAN,
        staged={"notes.md": b"n\n"},
        write_set={"notes.md"},
    )
    assert result.unattributed_snapshot is not None
    producers = [h["producer"]["kind"] for h in store.history()]
    assert "unattributed" in producers


def test_dirty_overlap_blocks(tmp_path: Path) -> None:
    store = mkroot(tmp_path)
    (tmp_path / "object.json").write_text('{"x": 8}\n', encoding="utf-8")
    with pytest.raises(BlockedError):
        store.commit(
            command="testop",
            args={},
            producer=HUMAN,
            staged={"object.json": b'{"x": 99}\n'},
            write_set={"object.json"},
        )


def test_second_writer_gets_lock_held(tmp_path: Path) -> None:
    store = mkroot(tmp_path)
    acquire(store.lock_path, "op-HELD", "other")  # simulate a held lock
    (tmp_path / "object.json").write_text('{"x": 5}\n', encoding="utf-8")
    with pytest.raises(ToolFailureError) as exc:
        store.checkpoint(by="human")
    assert exc.value.exit_code == 4
