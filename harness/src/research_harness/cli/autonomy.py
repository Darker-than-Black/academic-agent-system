"""`rh autonomy show|set` (M3-06, FR-33). Changing the level is human-only."""

from __future__ import annotations

import argparse
from typing import Any

from research_harness.cli.context import object_root
from research_harness.core.envelope import build_envelope
from research_harness.gates.interactive import is_human_channel
from research_harness.lifecycle import autonomy as autonomy_mod

_COMMAND = "autonomy"


def register(sub: argparse._SubParsersAction) -> None:
    au = sub.add_parser(_COMMAND, help="Show or set the object autonomy level.")
    sa = au.add_subparsers(dest="autonomy_action", metavar="action", required=True)
    sa.add_parser("show", help="Show the current autonomy level.")
    st = sa.add_parser("set", help="Set the autonomy level (human terminal only).")
    st.add_argument("level", choices=list(autonomy_mod.LEVELS))


def handles(command: str) -> bool:
    return command == _COMMAND


def route(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = object_root(args)
    if args.autonomy_action == "show":
        level = autonomy_mod.read(root)
        return (
            build_envelope(
                command=_COMMAND,
                status="ok",
                lang=lang,
                message_key="autonomy.shown",
                message_params={"level": level},
                data={"autonomy": level},
            ),
            0,
        )
    # set — human-only (ASR-04).
    if not is_human_channel():
        return (
            build_envelope(
                command=_COMMAND,
                status="blocked",
                lang=lang,
                message_key="error.autonomy_human_only",
                next_actions=[{"who": "author", "action": f"rh autonomy set {args.level}"}],
            ),
            3,
        )
    level = autonomy_mod.set_level(root, args.level)
    return (
        build_envelope(
            command=_COMMAND,
            status="ok",
            lang=lang,
            message_key="autonomy.set",
            message_params={"level": level},
            data={"autonomy": level},
        ),
        0,
    )
