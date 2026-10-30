"""`rh structure show|check|add|move|retitle|remove|renumber|sync` (M1-07)."""

from __future__ import annotations

import argparse
from typing import Any

from research_harness.cli.context import main_language, object_root
from research_harness.core.envelope import build_envelope
from research_harness.structure import model, ops
from research_harness.structure.checks import check_structure
from research_harness.structure.naming import compute_paths

_COMMAND = "structure"


def register(sub: argparse._SubParsersAction) -> None:
    st = sub.add_parser(_COMMAND, help="Structure tree and units.")
    sa = st.add_subparsers(dest="structure_action", metavar="action", required=True)
    sa.add_parser("show", help="Print the unit tree.")
    sa.add_parser("check", help="Validate structure invariants (02 §7.2).")
    sa.add_parser("renumber", help="Recompute folder names/numbers.")
    sa.add_parser("sync", help="Make folders + front matter match structure.yaml.")
    a = sa.add_parser("add", help="Add a unit.")
    a.add_argument("--kind", required=True)
    a.add_argument("--title")
    a.add_argument("--parent")
    a.add_argument("--index", type=int)
    m = sa.add_parser("move", help="Move a unit to a new index among its siblings.")
    m.add_argument("--unit", required=True)
    m.add_argument("--index", type=int, required=True)
    r = sa.add_parser("retitle", help="Change a unit's title.")
    r.add_argument("--unit", required=True)
    r.add_argument("--title", required=True)
    rm = sa.add_parser("remove", help="Remove a unit and its folder.")
    rm.add_argument("--unit", required=True)


def handles(command: str) -> bool:
    return command == _COMMAND


def route(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = object_root(args)
    ml = main_language(root)
    action = args.structure_action

    if action == "show":
        data = model.load(root)
        labels = model.resolve_labels(data, ml)
        units = model.parse_units(data)
        paths = compute_paths(units, labels)
        return _ok(lang, "structure.shown", {"paths": paths})
    if action == "check":
        findings = check_structure(root, ml)
        blocked = any(f["severity"] == "blocker" for f in findings)
        env = build_envelope(
            command=_COMMAND,
            status="blocked" if blocked else ("partial" if findings else "ok"),
            lang=lang,
            message_key="structure.checked",
            message_params={"n": len(findings)},
            findings=findings,
            data={"finding_count": len(findings)},
        )
        return env, (3 if blocked else 0)
    if action == "renumber":
        return _ok(lang, "structure.renumbered", ops.renumber(root, ml))
    if action == "sync":
        return _ok(lang, "structure.synced", ops.sync(root, ml))
    if action == "add":
        new_id = ops.add_unit(
            root,
            kind=args.kind,
            title=args.title,
            parent_id=args.parent,
            index=args.index,
            main_language=ml,
        )
        return _ok(lang, "structure.added", {"unit": new_id})
    if action == "move":
        return _ok(lang, "structure.moved", ops.move(root, args.unit, args.index, ml))
    if action == "retitle":
        return _ok(lang, "structure.retitled", ops.retitle(root, args.unit, args.title, ml))
    if action == "remove":
        return _ok(lang, "structure.removed", ops.remove(root, args.unit, ml))
    raise ValueError(action)


def _ok(lang: str, key: str, data: dict[str, Any]) -> tuple[dict[str, Any], int]:
    return (
        build_envelope(command=_COMMAND, status="ok", lang=lang, message_key=key, data=data),
        0,
    )
