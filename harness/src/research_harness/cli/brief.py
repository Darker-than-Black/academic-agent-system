"""`rh brief set|check|answer` (M2-07)."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

from research_harness.cli.context import object_root
from research_harness.core.envelope import build_envelope
from research_harness.units import brief as brief_mod


def register(sub: argparse._SubParsersAction) -> None:
    br = sub.add_parser("brief", help="Unit briefs and author contribution points.")
    ba = br.add_subparsers(dest="brief_action", metavar="action", required=True)
    bset = ba.add_parser("set", help="Set a unit brief from a file.")
    bset.add_argument("unit")
    bset.add_argument("--file", required=True)
    bchk = ba.add_parser("check", help="Check a unit brief.")
    bchk.add_argument("unit")
    bans = ba.add_parser("answer", help="Record an author's answer to a contribution point.")
    bans.add_argument("unit")
    bans.add_argument("--point", required=True)
    bans.add_argument("--value", required=True)


def handles(command: str) -> bool:
    return command == "brief"


def route(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = object_root(args)
    action = args.brief_action
    if action == "set":
        data = yaml.safe_load(Path(args.file).read_text(encoding="utf-8")) or {}
        brief = brief_mod.save_brief(root, args.unit, data)
        findings = brief_mod.check_brief(root, args.unit)
        blocked = any(f["severity"] == "blocker" for f in findings)
        return (
            build_envelope(
                command="brief",
                status="blocked" if blocked else ("partial" if findings else "ok"),
                lang=lang,
                message_key="brief.set",
                message_params={"unit": args.unit},
                findings=findings,
                data={"brief": brief},
            ),
            3 if blocked else 0,
        )
    if action == "check":
        findings = brief_mod.check_brief(root, args.unit)
        blocked = any(f["severity"] == "blocker" for f in findings)
        return (
            build_envelope(
                command="brief",
                status="blocked" if blocked else ("partial" if findings else "ok"),
                lang=lang,
                message_key="brief.checked",
                message_params={"unit": args.unit},
                findings=findings,
            ),
            3 if blocked else 0,
        )
    brief = brief_mod.answer_point(root, args.unit, args.point, args.value)
    return (
        build_envelope(
            command="brief",
            status="ok",
            lang=lang,
            message_key="brief.answered",
            message_params={"point": args.point},
            data={"brief": brief},
        ),
        0,
    )
