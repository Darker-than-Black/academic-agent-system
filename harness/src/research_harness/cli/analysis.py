"""`rh analysis init` / `rh analysis sandbox` (M3-18, analysis-sandbox.md).

``init`` creates the per-object ``uv`` project; ``sandbox`` reports how the
network will be isolated for runs (namespace vs Python guard). Executing scripts
is M3-19."""

from __future__ import annotations

import argparse
from typing import Any

from research_harness.analysis import project, sandbox
from research_harness.cli.context import object_root
from research_harness.core.envelope import build_envelope

_COMMAND = "analysis"


def register(sub: argparse._SubParsersAction) -> None:
    an = sub.add_parser(_COMMAND, help="Analysis sandbox (per-object uv project).")
    sa = an.add_subparsers(dest="analysis_action", metavar="action", required=True)
    sa.add_parser("init", help="Create the per-object analysis project with pinned packages.")
    sa.add_parser("sandbox", help="Show the network-isolation capability for runs.")


def handles(command: str) -> bool:
    return command == _COMMAND


def route(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = object_root(args)
    if args.analysis_action == "init":
        report = project.init(root)
        return (
            build_envelope(
                command=_COMMAND,
                status="ok",
                lang=lang,
                message_key="analysis.init",
                message_params={"created": report["created"]},
                data=report,
            ),
            0,
        )
    caps = sandbox.capabilities()
    return (
        build_envelope(
            command=_COMMAND,
            status="ok",
            lang=lang,
            message_key="analysis.sandbox",
            message_params={"network": caps.network},
            data={"network": caps.network, "namespace": caps.namespace},
        ),
        0,
    )
