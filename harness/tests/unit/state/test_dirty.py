"""Dirty-set tests (02 §5.6)."""

from __future__ import annotations

from pathlib import Path

from research_harness.state.dirty import dirty_set
from research_harness.state.store import Store

HUMAN = {"kind": "human", "name": "t", "version": "0.1.0"}


def test_dirty_tracks_edit_add_remove(tmp_path: Path) -> None:
    (tmp_path / "object.json").write_text('{"x": 1}\n', encoding="utf-8")
    store = Store(tmp_path)
    store.init(HUMAN)
    assert dirty_set(tmp_path) == set()

    (tmp_path / "object.json").write_text('{"x": 2}\n', encoding="utf-8")
    (tmp_path / "new.md").write_text("new\n", encoding="utf-8")
    assert dirty_set(tmp_path) == {"object.json", "new.md"}

    store.checkpoint(by="human")
    assert dirty_set(tmp_path) == set()

    (tmp_path / "object.json").unlink()
    assert dirty_set(tmp_path) == {"object.json"}
