"""`rh results list` / `rh results check` (M3-19, ADR-009/FR-06).

``list`` shows result rows; ``check`` runs the tuple validators over every
own-numeric claim and blocks on any mismatch."""

from __future__ import annotations

import argparse
from typing import Any

from research_harness.analysis import rows as rows_mod
from research_harness.analysis import tuples
from research_harness.cli.context import object_root
from research_harness.core.envelope import build_envelope

_COMMAND = "results"


def register(sub: argparse._SubParsersAction) -> None:
    rs = sub.add_parser(_COMMAND, help="Result rows and tuple validators.")
    sa = rs.add_subparsers(dest="results_action", metavar="action", required=True)
    sa.add_parser("list", help="List result rows.")
    sa.add_parser("check", help="Validate own-numeric claims against result rows.")


def handles(command: str) -> bool:
    return command == _COMMAND


def route(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = object_root(args)
    if args.results_action == "list":
        items = rows_mod.load(root)
        return (
            build_envelope(
                command=_COMMAND,
                status="ok",
                lang=lang,
                message_key="results.list",
                message_params={"n": len(items)},
                data={"rows": items},
            ),
            0,
        )
    findings = tuples.check(root)
    blocked = bool(findings)
    return (
        build_envelope(
            command=_COMMAND,
            status="blocked" if blocked else "ok",
            lang=lang,
            message_key="results.check_blocked" if blocked else "results.check_ok",
            message_params={"n": len(findings)},
            findings=findings,
        ),
        3 if blocked else 0,
    )
