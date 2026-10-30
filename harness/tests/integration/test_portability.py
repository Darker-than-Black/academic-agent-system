"""An object survives being moved to another workspace at another path (T11)."""

from __future__ import annotations

import shutil
from pathlib import Path
from types import SimpleNamespace

from research_harness.cli import validate as cli_validate
from research_harness.state import snapshot as snap
from research_harness.state.store import Store
from research_harness.workspace.objects import create_object
from research_harness.workspace.workspace import Workspace


def _seed(tmp_path: Path) -> Path:
    ws = Workspace.init(tmp_path / "ws-a" / "Projects")
    _oid, folder = create_object(ws, title="Портативна", kind="article", document_kind="article")
    (folder / "manuscript").mkdir(exist_ok=True)
    (folder / "manuscript" / "draft.md").write_text("# Чернетка\n\nтекст\n", encoding="utf-8")
    Store(folder).checkpoint(by="human", note="content")
    return folder


def test_moved_object_keeps_snapshot_hash_and_has_no_absolute_paths(tmp_path: Path) -> None:
    src = _seed(tmp_path)
    original_current = snap.read_current(src)
    original_hash = snap.load_snapshot(src, original_current)["manifest_sha256"]

    dest = tmp_path / "elsewhere" / "deeper" / src.name
    dest.parent.mkdir(parents=True)
    shutil.copytree(src, dest)

    # Snapshot identity is path-independent (content-addressed, relative paths).
    assert snap.read_current(dest) == original_current
    assert snap.load_snapshot(dest, original_current)["manifest_sha256"] == original_hash

    # No stored record contains an absolute path from either location.
    needles = [str(src), str(dest), str(tmp_path)]
    for jf in dest.rglob("*.json"):
        text = jf.read_text(encoding="utf-8")
        assert not any(n in text for n in needles), f"absolute path leaked into {jf}"


def test_moved_object_validates_clean(tmp_path: Path) -> None:
    src = _seed(tmp_path)
    dest = tmp_path / "moved" / src.name
    dest.parent.mkdir(parents=True)
    shutil.copytree(src, dest)

    args = SimpleNamespace(
        scope="all", root=str(dest), known=None, schema=None, file=None, object=None, workspace=None
    )
    envelope, _code = cli_validate.run(args, "uk")
    assert envelope["status"] == "ok"
