"""Unit locks (M3-08, FR-41, T21)."""

from __future__ import annotations

from pathlib import Path

import pytest

from research_harness.core.errors import BlockedError
from research_harness.lifecycle import locks as lk


def test_lock_unlock_cycle(tmp_path: Path) -> None:
    assert not lk.is_locked(tmp_path, "U-ABCDEFGH")
    rec = lk.lock(tmp_path, "U-ABCDEFGH", reason="submitted", locked_by="author")
    assert rec["unit_id"] == "U-ABCDEFGH" and "at" in rec
    assert lk.is_locked(tmp_path, "U-ABCDEFGH")
    assert lk.unlock(tmp_path, "U-ABCDEFGH") is True
    assert not lk.is_locked(tmp_path, "U-ABCDEFGH")
    assert lk.unlock(tmp_path, "U-ABCDEFGH") is False


def test_assert_not_locked_blocks(tmp_path: Path) -> None:
    lk.lock(tmp_path, "U-ABCDEFGH", reason="r", locked_by="author")
    with pytest.raises(BlockedError):
        lk.assert_not_locked(tmp_path, "U-ABCDEFGH")
    # unlocked unit does not raise
    lk.assert_not_locked(tmp_path, "U-OTHER123")


def test_write_body_enforces_lock() -> None:
    # The write path imports and calls assert_not_locked (T21 wiring).
    import inspect

    from research_harness.units import write

    assert "assert_not_locked" in inspect.getsource(write.write_body)
    assert "assert_not_locked" in inspect.getsource(write.write_unit)
