"""Shared object/workspace resolution for CLI handlers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from research_harness.cli.state import resolve_object_root
from research_harness.workspace.workspace import Workspace


def object_root(args: Any) -> Path:
    """Resolve the object folder from --object, --root, or the cwd (.rh search)."""
    oid = getattr(args, "object", None)
    if oid:
        return Workspace.find(getattr(args, "workspace", None)).object_folder(oid)
    return resolve_object_root(getattr(args, "root", None))


def main_language(root: Path) -> str:
    import json

    obj = root / "object.json"
    if obj.is_file():
        try:
            return (
                json.loads(obj.read_text(encoding="utf-8")).get("languages", {}).get("main", "uk")
            )
        except json.JSONDecodeError:
            pass
    return "uk"
