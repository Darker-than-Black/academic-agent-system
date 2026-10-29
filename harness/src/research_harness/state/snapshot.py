"""Snapshots and the content-addressed blob store (02 §5.1, §5.2).

Adapted from AutoResearchClaw (MIT)
  @ be4ba4755bf1b52220f25e13b2293b5956590070 : researchclaw/pipeline/runner.py
  (functions _write_checkpoint, _write_heartbeat, read_checkpoint,
  resume_from_checkpoint — adapted, not the 1864-line file)
Changes: kept the "temp file in the same dir → fsync → atomic rename" write
pattern; the per-stage checkpoint.json is replaced by a snapshot manifest with a
content-addressed blob store; heartbeat metadata moved to the lock (state/lock.py)
and the resume resolution to state/recovery.py; no silent rerun of side effects.
See adoption record ADP-003 in harness/third_party/manifest.json.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from research_harness.core.clock import default_clock
from research_harness.core.hashing import file_hash
from research_harness.core.ids import new_snapshot_id

SKIP_TOP_DIRS = frozenset({".rh", "export", "work"})
# Gitignored foreign/private content: listed by hash only, blob never stored.
STORED_FALSE_PREFIXES = (
    "sources/inbox/",
    "sources/fulltext/",
    "sources/pagetext/",
    "materials/private/",
    "analysis/data/",
)


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write ``data`` via a temp file in the same dir, fsync, then rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=path.suffix)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _rel(root: Path, p: Path) -> str:
    return p.relative_to(root).as_posix()


def managed_files(root: Path) -> list[tuple[str, bool]]:
    """Return (relpath, stored) for every managed file (02 §5.2)."""
    out: list[tuple[str, bool]] = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = _rel(root, p)
        top = rel.split("/", 1)[0]
        if top in SKIP_TOP_DIRS:
            continue
        stored = not any(rel.startswith(pre) for pre in STORED_FALSE_PREFIXES)
        out.append((rel, stored))
    return out


def blob_path(root: Path, sha256: str) -> Path:
    return root / ".rh" / "objects" / sha256


def build_manifest(
    root: Path,
    *,
    operation: dict[str, Any],
    producer: dict[str, Any],
    parent: str | None,
    tags: list[str] | None = None,
    snapshot_id: str | None = None,
) -> dict[str, Any]:
    """Build a snapshot manifest for the current working tree."""
    files: list[dict[str, Any]] = []
    for rel, stored in managed_files(root):
        p = root / rel
        files.append(
            {
                "path": rel,
                "sha256": file_hash(p),
                "size": p.stat().st_size,
                "stored": stored,
            }
        )
    manifest: dict[str, Any] = {
        "schema_version": "0.2",
        "id": snapshot_id or new_snapshot_id(),
        "created_at": default_clock().now_rfc3339(),
        "producer": producer,
        "parent": parent,
        "operation": operation,
        "files": files,
        "tags": tags or [],
    }
    from research_harness.core.hashing import canonical_json_hash

    manifest["manifest_sha256"] = canonical_json_hash(manifest)
    return manifest


def write_blobs(root: Path, manifest: dict[str, Any]) -> None:
    """Write missing blobs for every stored=true file (dedup by hash)."""
    for entry in manifest["files"]:
        if not entry["stored"]:
            continue
        bp = blob_path(root, entry["sha256"])
        if bp.exists():
            continue
        atomic_write_bytes(bp, (root / entry["path"]).read_bytes())


def write_snapshot(root: Path, manifest: dict[str, Any]) -> Path:
    """Write the snapshot manifest atomically. This is the commit point."""
    path = root / ".rh" / "snapshots" / f"{manifest['id']}.json"
    atomic_write_bytes(path, json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"))
    return path


def load_snapshot(root: Path, snapshot_id: str) -> dict[str, Any]:
    path = root / ".rh" / "snapshots" / f"{snapshot_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def all_snapshots(root: Path) -> list[dict[str, Any]]:
    snaps_dir = root / ".rh" / "snapshots"
    if not snaps_dir.is_dir():
        return []
    out = []
    for p in snaps_dir.glob("*.json"):
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return out


def read_current(root: Path) -> str | None:
    cur = root / ".rh" / "CURRENT"
    if not cur.exists():
        return None
    text = cur.read_text(encoding="utf-8").strip()
    return text or None


def write_current(root: Path, snapshot_id: str) -> None:
    atomic_write_bytes(root / ".rh" / "CURRENT", (snapshot_id + "\n").encode("utf-8"))


def materialize(root: Path, manifest: dict[str, Any]) -> None:
    """Write every stored=true file in ``manifest`` from its blob into the tree."""
    for entry in manifest["files"]:
        if not entry["stored"]:
            continue
        data = blob_path(root, entry["sha256"]).read_bytes()
        atomic_write_bytes(root / entry["path"], data)


def missing_blobs(root: Path, manifest: dict[str, Any]) -> list[str]:
    """Return shas of stored=true files whose blob is absent (corrupt state)."""
    return [
        e["sha256"]
        for e in manifest["files"]
        if e["stored"] and not blob_path(root, e["sha256"]).exists()
    ]
