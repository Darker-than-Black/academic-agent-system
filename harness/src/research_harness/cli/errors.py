"""`rh errors profile choose` / `rh errors check [--unit U]` (M3-13, FR-51)."""

from __future__ import annotations

import argparse
from typing import Any

from research_harness.cli.context import main_language, object_root
from research_harness.core.envelope import build_envelope
from research_harness.core.errors import InvalidInputError
from research_harness.integrity import errors as errors_mod
from research_harness.units.write import read_body
from research_harness.workspace import author as author_mod
from research_harness.workspace.workspace import Workspace

_COMMAND = "errors"


def register(sub: argparse._SubParsersAction) -> None:
    ep = sub.add_parser(_COMMAND, help="Typical-errors profile and check.")
    sa = ep.add_subparsers(dest="errors_action", metavar="action", required=True)
    prof = sa.add_parser("profile", help="Manage the typical-errors profile.")
    pa = prof.add_subparsers(dest="profile_action", metavar="action", required=True)
    choose = pa.add_parser("choose", help="Choose typical-error categories.")
    choose.add_argument("--category", action="append", required=True, dest="categories")
    choose.add_argument("--voice", default=None, choices=["I", "we", "impersonal"])
    chk = sa.add_parser("check", help="Report typical errors in a unit (never edits).")
    chk.add_argument("--unit", required=True)


def handles(command: str) -> bool:
    return command == _COMMAND


def _author_root(args: Any):
    ws = Workspace.find(getattr(args, "workspace", None))
    return author_mod.author_dir(ws)


def route(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    if args.errors_action == "profile":
        try:
            profile = errors_mod.choose(_author_root(args), args.categories, args.voice)
        except ValueError as exc:
            raise InvalidInputError("error.errors_unknown_category") from exc
        return (
            build_envelope(
                command=_COMMAND,
                status="ok",
                lang=lang,
                message_key="errors.chosen",
                message_params={"n": len(profile["chosen"])},
                data={"profile": profile},
            ),
            0,
        )
    # check
    root = object_root(args)
    text = read_body(root, args.unit)
    profile = errors_mod.load_profile(_author_root(args))
    findings = errors_mod.check_text(
        text, chosen=errors_mod.chosen_ids(profile), lang=main_language(root)
    )
    status = "partial" if findings else "ok"
    return (
        build_envelope(
            command=_COMMAND,
            status=status,
            lang=lang,
            message_key="errors.checked",
            message_params={"n": len(findings), "unit": args.unit},
            findings=findings,
            data={"unit": args.unit},
        ),
        0,
    )
