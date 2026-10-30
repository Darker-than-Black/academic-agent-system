"""Object creation and rename (01 §4, 02 §4.1, FR-42, FR-44, T45)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from research_harness.core.clock import default_clock
from research_harness.state.snapshot import atomic_write_bytes
from research_harness.state.store import Store
from research_harness.workspace import author
from research_harness.workspace.naming import object_folder_name

if TYPE_CHECKING:
    from research_harness.workspace.workspace import Workspace

HUMAN = {"kind": "human", "name": "rh", "version": "0.1.0"}


def _wj(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_bytes(path, (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def create_object(
    ws: Workspace,
    *,
    title: str,
    kind: str,
    document_kind: str = "unknown",
    operation_mode: str = "create",
    study_kind: str = "unknown",
    languages: dict[str, Any] | None = None,
    autonomy: str | None = None,
    stages: dict[str, Any] | None = None,
    structure_units: list[dict[str, Any]] | None = None,
) -> tuple[str, Path]:
    oid = ws.allocate_object_id(kind)
    folder = ws.root / object_folder_name(title, oid)
    folder.mkdir(parents=True)
    for sub in ("intake", "materials", "profiles", "manuscript", "approvals"):
        (folder / sub).mkdir(parents=True, exist_ok=True)

    import yaml

    atomic_write_bytes(
        folder / "structure.yaml",
        yaml.safe_dump(
            {
                "schema_version": "0.2",
                "object_id": oid,
                "labels": {},
                "units": structure_units or [],
            },
            allow_unicode=True,
            sort_keys=False,
        ).encode("utf-8"),
    )
    _wj(
        folder / "materials" / "manifest.json",
        {"schema_version": "0.2", "id": oid, "materials": []},
    )

    obj = {
        "schema_version": "0.2",
        "id": oid,
        "created_at": default_clock().now_rfc3339(),
        "producer": HUMAN,
        "kind": kind,
        "title": title,
        "document_kind": document_kind,
        "operation_mode": operation_mode,
        "study_kind": study_kind,
        "languages": languages or {"main": "uk", "abstracts": ["uk"]},
        "autonomy": autonomy or author.read_profile(ws).get("default_autonomy", "gates"),
        "author_pins": author.current_pin(ws),
        "stages": stages or {},
        "counters": {},
        "rename_history": [],
    }
    _wj(folder / "object.json", obj)

    Store(folder).init(HUMAN)
    ws.register_object(oid, kind, folder.name)
    return oid, folder


def rename_object(ws: Workspace, oid: str, new_title: str) -> Path:
    folder = ws.object_folder(oid)
    obj_path = folder / "object.json"
    obj = json.loads(obj_path.read_text(encoding="utf-8"))
    old_title = obj["title"]
    obj["title"] = new_title
    obj.setdefault("rename_history", []).append(
        {"from_title": old_title, "to_title": new_title, "at": default_clock().now_rfc3339()}
    )
    _wj(obj_path, obj)
    # Commit the title change before moving the folder, so the snapshot is intact.
    Store(folder).checkpoint(by="human", note=f"rename to {new_title}")

    new_folder = ws.root / object_folder_name(new_title, oid)
    if new_folder != folder:
        if new_folder.exists():
            raise FileExistsError(new_folder)
        os.replace(folder, new_folder)
    ws.register_object(oid, obj["kind"], new_folder.name)
    return new_folder
