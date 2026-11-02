"""`rh figure add|build|check|list` (M3-20, analysis-sandbox.md, FR-18)."""

from __future__ import annotations

import argparse
from typing import Any

from research_harness.analysis import figures
from research_harness.cli.context import object_root
from research_harness.core.envelope import build_envelope

_COMMAND = "figure"


def register(sub: argparse._SubParsersAction) -> None:
    fg = sub.add_parser(_COMMAND, help="Figures built from result rows (rebuild and invalidate).")
    sa = fg.add_subparsers(dest="figure_action", metavar="action", required=True)
    add = sa.add_parser("add", help="Define a figure (rows + plotting script).")
    add.add_argument("--script", required=True)
    add.add_argument("--row", dest="rows", action="append", default=None, help="Result row id.")
    add.add_argument("--format", dest="fmt", default="svg", choices=["svg", "png"])
    bl = sa.add_parser("build", help="Rebuild a figure from its rows and script.")
    bl.add_argument("fig_id")
    sa.add_parser("check", help="Report stale figures.")
    sa.add_parser("list", help="List figures.")


def handles(command: str) -> bool:
    return command == _COMMAND


def route(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = object_root(args)
    action = args.figure_action
    if action == "add":
        rec = figures.add(root, script=args.script, row_ids=args.rows or [], fmt=args.fmt)
        return _ok("figure.added", {"id": rec["id"]}, {"figure": rec}, lang)
    if action == "build":
        rec = figures.build(root, args.fig_id)
        return _ok("figure.built", {"id": rec["id"]}, {"figure": rec}, lang)
    if action == "list":
        ids = figures.list_ids(root)
        return _ok("figure.list", {"n": len(ids)}, {"figures": ids}, lang)
    findings = figures.stale_findings(root)
    blocked = bool(findings)
    return (
        build_envelope(
            command=_COMMAND,
            status="partial" if blocked else "ok",
            lang=lang,
            message_key="figure.stale" if blocked else "figure.fresh",
            message_params={"n": len(findings)},
            findings=findings,
        ),
        0,
    )


def _ok(key: str, params: dict, data: dict, lang: str) -> tuple[dict[str, Any], int]:
    return (
        build_envelope(
            command=_COMMAND,
            status="ok",
            lang=lang,
            message_key=key,
            message_params=params,
            data=data,
        ),
        0,
    )
