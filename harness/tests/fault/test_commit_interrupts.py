"""Fault-injection tests for the commit protocol (02 §5.3, §5.5; T10).

Each of the nine commit steps is interrupted by hard-killing a subprocess, then
recovery runs and the invariants are asserted: CURRENT points at a valid
snapshot, the working tree equals CURRENT, no committed snapshot lacks a blob,
and repeating the operation does not create a second snapshot.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from research_harness.core.hashing import file_hash
from research_harness.state import snapshot as snap
from research_harness.state.faults import STEPS
from research_harness.state.recovery import recover
from research_harness.state.store import Store

HUMAN = {"kind": "human", "name": "t", "version": "0.1.0"}

WORKER = """
import sys
from pathlib import Path
from research_harness.state.store import Store
root = Path(sys.argv[1])
Store(root).commit(
    command="testop", args={"k": 1},
    producer={"kind": "human", "name": "t", "version": "0.1.0"},
    staged={"manuscript/01/text.md": b"hello\\n"},
    write_set={"manuscript/01/text.md"},
)
"""


def _fresh_root(base: Path, name: str) -> Path:
    root = base / name
    root.mkdir(parents=True)
    (root / "object.json").write_text('{"x": 1}\n', encoding="utf-8")
    Store(root).init(HUMAN)
    return root


def _assert_consistent(root: Path) -> None:
    cur = snap.read_current(root)
    assert cur is not None
    manifest = snap.load_snapshot(root, cur)
    assert snap.missing_blobs(root, manifest) == []
    managed = {rel for rel, _ in snap.managed_files(root)}
    assert managed == {e["path"] for e in manifest["files"]}
    for e in manifest["files"]:
        if e["stored"]:
            assert file_hash(root / e["path"]) == e["sha256"]


def test_kill_at_each_step_then_recover(tmp_path: Path) -> None:
    worker = tmp_path / "worker.py"
    worker.write_text(WORKER, encoding="utf-8")

    for step in STEPS:
        root = _fresh_root(tmp_path, f"root_{step}")
        env = {**os.environ, "RH_TEST_MODE": "1", "RH_FAULT_AT": step, "RH_FAULT_KILL": "1"}
        proc = subprocess.run(
            [sys.executable, str(worker), str(root)], env=env, capture_output=True
        )
        assert proc.returncode == 99, f"step {step}: expected hard-exit 99, got {proc.returncode}"

        recover(root, repair=True)
        _assert_consistent(root)


def test_repeat_operation_is_idempotent(tmp_path: Path) -> None:
    root = _fresh_root(tmp_path, "idem")
    store = Store(root)

    def do() -> str:
        return store.commit(
            command="testop",
            args={"k": 1},
            producer=HUMAN,
            staged={"manuscript/01/text.md": b"hello\n"},
            write_set={"manuscript/01/text.md"},
        ).snapshot_id

    first = do()
    before = len(store.history())
    second = do()
    assert second == first
    assert len(store.history()) == before


def test_truncated_events_quarantined_and_reported(tmp_path: Path) -> None:
    root = _fresh_root(tmp_path, "trunc")
    with open(root / ".rh" / "events.jsonl", "a", encoding="utf-8") as fh:
        fh.write('{"bad":')
    findings = recover(root, repair=True)
    assert any(f["check_id"] == "state.events_truncated" for f in findings)
    _assert_consistent(root)
