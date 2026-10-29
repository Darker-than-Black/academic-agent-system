"""Dirty set: managed files changed since CURRENT (02 §5.6)."""

from __future__ import annotations

from pathlib import Path

from research_harness.core.hashing import file_hash
from research_harness.state import snapshot as snap


def current_file_hashes(root: Path) -> dict[str, str]:
    """Path → sha256 recorded in the CURRENT snapshot (empty if none)."""
    cur = snap.read_current(root)
    if cur is None:
        return {}
    manifest = snap.load_snapshot(root, cur)
    return {e["path"]: e["sha256"] for e in manifest["files"]}


def working_file_hashes(root: Path) -> dict[str, str]:
    return {rel: file_hash(root / rel) for rel, _stored in snap.managed_files(root)}


def dirty_set(root: Path) -> set[str]:
    """Managed files added, removed or changed relative to CURRENT."""
    recorded = current_file_hashes(root)
    working = working_file_hashes(root)
    dirty: set[str] = set()
    for path, h in working.items():
        if recorded.get(path) != h:
            dirty.add(path)
    for path in recorded:
        if path not in working:
            dirty.add(path)
    return dirty


def overlaps(dirty: set[str], write_set: set[str]) -> set[str]:
    return dirty & write_set
