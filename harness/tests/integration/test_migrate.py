"""Migrations create a new snapshot; tagged snapshots stay immutable (T40)."""

from __future__ import annotations

import json
from pathlib import Path

from research_harness.core.hashing import file_hash
from research_harness.migrate import registry, runner
from research_harness.state import snapshot as snap
from research_harness.state.store import Store
from research_harness.workspace.objects import create_object
from research_harness.workspace.workspace import Workspace


def _object(tmp_path: Path) -> Path:
    registry.ensure_test_migration()
    ws = Workspace.init(tmp_path / "Projects")
    _oid, folder = create_object(ws, title="Міграція", kind="article", document_kind="article")
    (folder / "migrate-test.json").write_text(
        json.dumps({"schema_version": "0.2", "old_field": "value"}) + "\n", encoding="utf-8"
    )
    Store(folder).checkpoint(by="human", note="seed migrate-test")
    return folder


def test_migration_creates_new_snapshot_and_renames_field(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    before = snap.read_current(folder)
    result = runner.migrate(folder, "0.3")
    assert result["snapshot"] != before
    doc = json.loads((folder / "migrate-test.json").read_text(encoding="utf-8"))
    assert doc["schema_version"] == "0.3"
    assert "new_field" in doc and "old_field" not in doc


def test_published_snapshot_and_blobs_unchanged(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    published = snap.read_current(folder)
    runner.tag_snapshot(folder, "published", published)

    snap_file = folder / ".rh" / "snapshots" / f"{published}.json"
    snap_hash_before = file_hash(snap_file)
    manifest = snap.load_snapshot(folder, published)
    blob_hashes = {e["sha256"] for e in manifest["files"] if e.get("stored", True)}

    runner.migrate(folder, "0.3")

    assert file_hash(snap_file) == snap_hash_before  # published snapshot file untouched
    for h in blob_hashes:
        blob = snap.blob_path(folder, h)
        assert blob.is_file() and file_hash(blob) == h  # every published blob intact
    assert snap.read_current(folder) != published  # new current snapshot
    assert runner.load_tags(folder)["published"] == published


def test_dry_run_changes_nothing(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    before_current = snap.read_current(folder)
    result = runner.migrate(folder, "0.3", dry_run=True)
    assert result["snapshot"] is None and result["plans"]
    doc = json.loads((folder / "migrate-test.json").read_text(encoding="utf-8"))
    assert doc["schema_version"] == "0.2" and "old_field" in doc
    assert snap.read_current(folder) == before_current
