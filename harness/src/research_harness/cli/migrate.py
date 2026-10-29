"""`rh migrate --to V [--dry-run]` (M1-13, 02 §11)."""

from __future__ import annotations

import argparse
from typing import Any

from research_harness.cli.context import object_root
from research_harness.core.envelope import build_envelope
from research_harness.migrate import runner

_COMMAND = "migrate"


def register(sub: argparse._SubParsersAction) -> None:
    mg = sub.add_parser(_COMMAND, help="Migrate current state to a schema version.")
    mg.add_argument("--to", dest="to_version", required=True)
    mg.add_argument("--dry-run", action="store_true")


def handles(command: str) -> bool:
    return command == _COMMAND


def route(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = object_root(args)
    result = runner.migrate(root, args.to_version, dry_run=args.dry_run)
    if not result["plans"]:
        key = "migrate.nothing"
    elif result["dry_run"]:
        key = "migrate.dry_run"
    else:
        key = "migrate.done"
    return (
        build_envelope(
            command=_COMMAND,
            status="ok",
            lang=lang,
            message_key=key,
            message_params={"to": args.to_version, "n": len(result["plans"])},
            data=result,
        ),
        0,
    )
