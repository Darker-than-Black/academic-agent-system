"""The workspace: ``.rh-workspace.json``, per-year ID counters, object index
(01 §4, 02 §3.1)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_harness.core.clock import default_clock
from research_harness.core.errors import InvalidInputError
from research_harness.core.ids import new_workspace_id, object_id
from research_harness.core.paths import nfc_lookup
from research_harness.state.snapshot import atomic_write_bytes
from research_harness.workspace import author
from research_harness.workspace.naming import id_from_folder

WORKSPACE_FILE = ".rh-workspace.json"
_KIND_LETTER = {"article": "A", "thesis": "T"}


class Workspace:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    @property
    def file(self) -> Path:
        return self.root / WORKSPACE_FILE

    def load(self) -> dict[str, Any]:
        return json.loads(self.file.read_text(encoding="utf-8"))

    def save(self, data: dict[str, Any]) -> None:
        atomic_write_bytes(
            self.file, (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        )

    # --- discovery / creation ---
    @classmethod
    def find(cls, start: str | Path | None = None) -> Workspace:
        base = Path(start) if start else Path.cwd()
        for d in [base, *base.parents]:
            if (d / WORKSPACE_FILE).is_file():
                return cls(d)
        raise InvalidInputError("error.no_workspace")

    @classmethod
    def init(cls, path: str | Path) -> Workspace:
        root = Path(path)
        root.mkdir(parents=True, exist_ok=True)
        ws = cls(root)
        if ws.file.exists():
            raise InvalidInputError("error.workspace_exists")
        ws.save(
            {
                "schema_version": "0.2",
                "id": new_workspace_id(),
                "created_at": default_clock().now_rfc3339(),
                "counters": {},
                "objects": [],
            }
        )
        author.init_author(ws)
        return ws

    # --- object ids / index ---
    def allocate_object_id(self, kind: str) -> str:
        if kind not in _KIND_LETTER:
            raise InvalidInputError("error.bad_kind")
        data = self.load()
        year = int(default_clock().now_rfc3339()[:4])
        letter = _KIND_LETTER[kind]
        counters = data.setdefault("counters", {}).setdefault(letter, {})
        n = int(counters.get(str(year), 0)) + 1
        counters[str(year)] = n
        self.save(data)
        return object_id(kind, year, n)

    def register_object(self, oid: str, kind: str, folder: str) -> None:
        data = self.load()
        objs = [o for o in data.get("objects", []) if o["id"] != oid]
        objs.append({"id": oid, "kind": kind, "folder": folder})
        data["objects"] = sorted(objs, key=lambda o: o["id"])
        self.save(data)

    def object_folder(self, oid: str) -> Path:
        data = self.load()
        for o in data.get("objects", []):
            if o["id"] == oid:
                found = nfc_lookup(self.root, o["folder"])
                if found is not None:
                    return found
        # fall back to a scan of the folders on disk
        for child in self.root.iterdir():
            if child.is_dir() and id_from_folder(child.name) == oid:
                return child
        raise InvalidInputError("error.no_object")

    def reindex(self) -> list[dict[str, Any]]:
        """Rebuild the object index from folders on disk (folders win, 02 §3.1)."""
        data = self.load()
        objects: list[dict[str, Any]] = []
        for child in sorted(self.root.iterdir()):
            if not child.is_dir():
                continue
            oid = id_from_folder(child.name)
            if oid is None:
                continue
            kind = "unknown"
            obj_file = child / "object.json"
            if obj_file.is_file():
                try:
                    kind = json.loads(obj_file.read_text(encoding="utf-8")).get("kind", "unknown")
                except json.JSONDecodeError:
                    pass
            objects.append({"id": oid, "kind": kind, "folder": child.name})
        data["objects"] = objects
        self.save(data)
        return objects
