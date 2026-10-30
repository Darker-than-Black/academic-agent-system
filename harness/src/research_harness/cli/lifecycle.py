"""`rh status`, `rh start`, `rh continue` (M1-11, FR-28, FR-41)."""

from __future__ import annotations

import argparse
from typing import Any

from research_harness.cli.context import object_root
from research_harness.core.envelope import build_envelope
from research_harness.lifecycle import routing
from research_harness.lifecycle import status as status_mod
from research_harness.workspace.workspace import Workspace

_COMMANDS = {"status", "start", "continue"}


def register(sub: argparse._SubParsersAction) -> None:
    st = sub.add_parser("status", help="Status report (03 §3).")
    st.add_argument("--all", action="store_true", help="List all objects in the workspace.")
    sr = sub.add_parser("start", help="Start a new object or route an existing one.")
    sr.add_argument("title")
    sr.add_argument("--kind", choices=["article", "thesis"], default="article")
    sr.add_argument("--mode", default="create")
    sub.add_parser("continue", help="Recovery report, status and the next action (no changes).")


def handles(command: str) -> bool:
    return command in _COMMANDS


def route(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    if args.command == "start":
        return _start(args, lang)
    if args.command == "continue":
        return _continue(args, lang)
    return _status(args, lang)


def _status(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    if getattr(args, "all", False):
        ws = Workspace.find(getattr(args, "workspace", None))
        objs = []
        for o in ws.list_objects():
            try:
                rep = status_mod.build_report(ws.object_folder(o["id"]), lang)
                objs.append(
                    {
                        "id": o["id"],
                        "stage": rep["stage"]["current"],
                        "blockers": len(rep["blockers"]),
                    }
                )
            except Exception:  # noqa: BLE001 - a broken object should not hide the rest
                objs.append({"id": o["id"], "stage": "unknown", "blockers": 0})
        return build_envelope(
            command="status",
            status="ok",
            lang=lang,
            message_key="status.listed",
            message_params={"n": len(objs)},
            data={"objects": objs},
        ), 0

    root = object_root(args)
    report = status_mod.build_report(root, lang)
    text = (
        status_mod.render_text(report, lang) if getattr(args, "format", "json") == "text" else None
    )
    data = dict(report)
    if text is not None:
        data["_text"] = text
    return build_envelope(
        command="status",
        status="ok",
        lang=lang,
        message_key="status.shown",
        message_params={"id": report["object"]["id"]},
        data=data,
    ), 0


def _start(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    ws = Workspace.find(getattr(args, "workspace", None))
    res = routing.start(ws, title=args.title, kind=args.kind, mode=args.mode, lang=lang)
    if res["result"] == "mode_unsupported":
        return build_envelope(
            command="start",
            status="invalid",
            lang=lang,
            message_key="error.start_mode_m3",
            message_params={"mode": res["mode"]},
        ), 2
    if res["result"] == "ambiguous":
        return build_envelope(
            command="start",
            status="invalid",
            lang=lang,
            message_key="error.start_ambiguous",
            message_params={"n": len(res["candidates"])},
            data={"candidates": res["candidates"]},
        ), 2
    return build_envelope(
        command="start",
        status="ok",
        lang=lang,
        message_key="start.created",
        message_params={"id": res["oid"]},
        data={
            "object": res["oid"],
            "folder": res["folder"],
            "questions": res["questions"],
            "prefilled": res["prefilled"],
        },
    ), 0


def _continue(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = object_root(args)
    res = routing.continue_object(root, lang)
    quarantined = res["status"]["locks_and_recovery"]["quarantined"]
    status = "partial" if (res["recovery"] or quarantined) else "ok"
    return build_envelope(
        command="continue",
        status=status,
        lang=lang,
        message_key="continue.done",
        message_params={"id": res["status"]["object"]["id"]},
        next_actions=[res["next_action"]],
        data=res,
    ), 0
