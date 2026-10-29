"""Lock tests (02 §5.4)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from research_harness.state.lock import LockHeld, acquire, holder_alive, read_lock, release


def test_acquire_and_second_fails(tmp_path: Path) -> None:
    lp = tmp_path / "lock"
    info = acquire(lp, "op-1", "cmd")
    assert read_lock(lp) == info
    with pytest.raises(LockHeld) as exc:
        acquire(lp, "op-2", "cmd2")
    assert exc.value.exit_code == 4
    assert exc.value.holder is not None and exc.value.holder.operation_id == "op-1"


def test_release(tmp_path: Path) -> None:
    lp = tmp_path / "lock"
    acquire(lp, "op-1", "cmd")
    release(lp)
    assert read_lock(lp) is None


def test_holder_alive_for_self(tmp_path: Path) -> None:
    lp = tmp_path / "lock"
    info = acquire(lp, "op-1", "cmd")
    assert info.pid == os.getpid()
    assert holder_alive(info) is True
