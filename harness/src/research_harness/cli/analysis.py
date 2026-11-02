"""`rh analysis init` / `rh analysis sandbox` (M3-18, analysis-sandbox.md).

``init`` creates the per-object ``uv`` project; ``sandbox`` reports how the
network will be isolated for runs (namespace vs Python guard). Executing scripts
is M3-19."""

from __future__ import annotations

import argparse
from typing import Any

from research_harness.analysis import project, runner, sandbox
from research_harness.cli.context import object_root
from research_harness.core.envelope import build_envelope

_COMMAND = "analysis"


def register(sub: argparse._SubParsersAction) -> None:
    an = sub.add_parser(_COMMAND, help="Analysis sandbox (per-object uv project).")
    sa = an.add_subparsers(dest="analysis_action", metavar="action", required=True)
    sa.add_parser("init", help="Create the per-object analysis project with pinned packages.")
    sa.add_parser("sandbox", help="Show the network-isolation capability for runs.")
    rn = sa.add_parser("run", help="Run a script in the sandbox (network off).")
    rn.add_argument("script", help="Path to the analysis script.")
    rn.add_argument("--dataset", dest="datasets", action="append", default=None)
    rn.add_argument("--seed", type=int, default=None)
    rn.add_argument("--purpose", default="analysis", choices=["analysis", "instrument_pilot"])


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
    if args.analysis_action == "run":
        report = runner.run(
            root,
            args.script,
            dataset_ids=args.datasets or [],
            seed=args.seed,
            purpose=args.purpose,
        )
        ok = report["status"] == "succeeded"
        return (
            build_envelope(
                command=_COMMAND,
                status="ok" if ok else "blocked",
                lang=lang,
                message_key="analysis.run_ok" if ok else "analysis.run_failed",
                message_params={"run": report["run_id"], "rows": report["rows"]},
                data=report,
            ),
            0 if ok else 3,
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
