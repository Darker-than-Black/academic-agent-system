"""`rh ethics check` — is A6 permitted under the ethics gate GE? (M3-07, FR-31)."""

from __future__ import annotations

import argparse
from typing import Any

from research_harness.cli.context import object_root
from research_harness.core.envelope import build_envelope
from research_harness.intake import answers as answers_mod
from research_harness.lifecycle import ethics as ethics_mod

_COMMAND = "ethics"


def register(sub: argparse._SubParsersAction) -> None:
    et = sub.add_parser(_COMMAND, help="Ethics gate (GE) status for A6.")
    sa = et.add_subparsers(dest="ethics_action", metavar="action", required=True)
    sa.add_parser("check", help="Check whether A6 is permitted (read-only).")


def handles(command: str) -> bool:
    return command == _COMMAND


def route(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = object_root(args)
    finding = ethics_mod.ethics_gate_finding(root)
    required = ethics_mod.requires_ethics(answers_mod.load(root))
    blocked = finding is not None
    return (
        build_envelope(
            command=_COMMAND,
            status="blocked" if blocked else "ok",
            lang=lang,
            message_key="ethics.blocked" if blocked else "ethics.ok",
            findings=[finding] if finding else [],
            data={"required": required, "a6_permitted": not blocked},
        ),
        3 if blocked else 0,
    )
