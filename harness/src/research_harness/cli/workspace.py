"""`rh init-workspace`, `rh author`, `rh rename`, `rh workspace` (M1-06)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from research_harness.core.envelope import build_envelope
from research_harness.workspace import author as author_mod
from research_harness.workspace.objects import rename_object
from research_harness.workspace.workspace import Workspace


def _ws(args: Any) -> Workspace:
    return Workspace.find(getattr(args, "workspace", None))


def init_workspace(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    ws = Workspace.init(args.path)
    env = build_envelope(
        command="init-workspace",
        status="ok",
        lang=lang,
        message_key="workspace.created",
        message_params={"path": str(ws.root)},
        data={"workspace_id": ws.load()["id"], "path": str(ws.root)},
    )
    return env, 0


def author(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    ws = _ws(args)
    if args.author_action == "show":
        return (
            build_envelope(
                command="author",
                status="ok",
                lang=lang,
                message_key="author.shown",
                data={"profile": author_mod.read_profile(ws)},
            ),
            0,
        )
    if args.author_action == "set":
        n = author_mod.set_field(ws, args.key, args.value)
        return (
            build_envelope(
                command="author",
                status="ok",
                lang=lang,
                message_key="author.updated",
                message_params={"key": args.key, "version": n},
                data={"key": args.key, "version": n},
            ),
            0,
        )
    if args.author_action == "pin":
        folder = ws.object_folder(args.object)
        _repin(ws, folder)
        return (
            build_envelope(
                command="author",
                status="ok",
                lang=lang,
                message_key="author.pinned",
                message_params={"object": args.object},
                data={"object": args.object, "pin": author_mod.current_pin(ws)},
            ),
            0,
        )
    raise ValueError(args.author_action)


def _repin(ws: Workspace, folder: Path) -> None:
    import json

    from research_harness.state.snapshot import atomic_write_bytes
    from research_harness.state.store import Store

    obj_path = folder / "object.json"
    obj = json.loads(obj_path.read_text(encoding="utf-8"))
    obj["author_pins"] = author_mod.current_pin(ws)
    atomic_write_bytes(
        obj_path, (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )
    Store(folder).checkpoint(by="human", note="re-pin author profile")


def rename(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    ws = _ws(args)
    new_folder = rename_object(ws, args.object, args.title)
    env = build_envelope(
        command="rename",
        status="ok",
        lang=lang,
        message_key="rename.done",
        message_params={"folder": new_folder.name},
        data={"object": args.object, "folder": new_folder.name},
    )
    return env, 0


def workspace(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    ws = _ws(args)
    if args.workspace_action == "reindex":
        objects = ws.reindex()
        return (
            build_envelope(
                command="workspace",
                status="ok",
                lang=lang,
                message_key="workspace.reindexed",
                message_params={"n": len(objects)},
                data={"objects": objects},
            ),
            0,
        )
    raise ValueError(args.workspace_action)
