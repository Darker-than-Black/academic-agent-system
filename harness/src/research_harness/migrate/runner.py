"""Apply migrations to the current state as a new snapshot; tags are immutable."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_harness.migrate import registry
from research_harness.state.snapshot import atomic_write_bytes
from research_harness.state.store import Store

PROTECTED_TAGS = ("submitted", "published")


def tags_path(root: Path) -> Path:
    return root / ".rh" / "tags.json"


def load_tags(root: Path) -> dict[str, str]:
    p = tags_path(root)
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def tag_snapshot(root: Path, tag: str, snapshot_id: str) -> None:
    tags = load_tags(root)
    tags[tag] = snapshot_id
    atomic_write_bytes(
        tags_path(root), (json.dumps(tags, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )


def plan(root: Path, to_version: str) -> list[dict[str, Any]]:
    """Return per-file migration plans {file, schema, from, to, steps} for current state."""
    out: list[dict[str, Any]] = []
    for filename, schema in registry.targets().items():
        fpath = root / filename
        if not fpath.is_file():
            continue
        doc = json.loads(fpath.read_text(encoding="utf-8"))
        cur = doc.get("schema_version")
        if cur == to_version:
            continue
        steps = registry.chain(schema, cur, to_version)
        if not steps:
            continue
        out.append(
            {"file": filename, "schema": schema, "from": cur, "to": to_version, "steps": len(steps)}
        )
    return out


def migrate(root: Path, to_version: str, *, dry_run: bool = False) -> dict[str, Any]:
    plans = plan(root, to_version)
    if dry_run or not plans:
        return {"dry_run": dry_run, "plans": plans, "snapshot": None}

    for p in plans:
        fpath = root / p["file"]
        doc = json.loads(fpath.read_text(encoding="utf-8"))
        for m in registry.chain(p["schema"], doc["schema_version"], to_version):
            doc = m.fn(doc)
            doc["schema_version"] = m.to_v
        atomic_write_bytes(
            fpath, (json.dumps(doc, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        )

    result = Store(root).checkpoint(by="human", note=f"migrate to {to_version}")
    return {"dry_run": False, "plans": plans, "snapshot": result.snapshot_id}
