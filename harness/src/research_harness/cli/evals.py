"""`rh eval run|report --suite S` (M1-15)."""

from __future__ import annotations

import argparse
from typing import Any

from research_harness.core.envelope import build_envelope
from research_harness.core.errors import InvalidInputError
from research_harness.evals import report as report_mod
from research_harness.evals import runner

_COMMAND = "eval"


def register(sub: argparse._SubParsersAction) -> None:
    ev = sub.add_parser(_COMMAND, help="Evaluation suite and gate report.")
    sa = ev.add_subparsers(dest="eval_action", metavar="action", required=True)
    rn = sa.add_parser("run", help="Run every case in a suite.")
    rn.add_argument("--suite", required=True)
    rn.add_argument("--case", help="Run only this case id.")
    rn.add_argument(
        "--run",
        help="Semantic cases: path to a host run artifact to score instead of the case default "
        "(a real С run replaces the committed synthetic one). Must be outside holdout (H1).",
    )
    rp = sa.add_parser("report", help="Show the latest report for a suite.")
    rp.add_argument("--suite", required=True)


def handles(command: str) -> bool:
    return command == _COMMAND


def route(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    if args.eval_action == "run":
        report = runner.run_suite(
            args.suite, only=getattr(args, "case", None), run_override=getattr(args, "run", None)
        )
        report["_text"] = report_mod.render_text(report)
        return (
            build_envelope(
                command=_COMMAND,
                status="ok" if report["all_pass"] else "partial",
                lang=lang,
                message_key="eval.ran",
                message_params={
                    "suite": args.suite,
                    "passed": report["passed"],
                    "total": report["total"],
                },
                data=report,
            ),
            0 if report["all_pass"] else 2,
        )

    report = runner.latest_report(args.suite)
    if report is None:
        raise InvalidInputError("error.eval_no_report")
    report["_text"] = report_mod.render_text(report)
    return (
        build_envelope(
            command=_COMMAND,
            status="ok" if report["all_pass"] else "partial",
            lang=lang,
            message_key="eval.reported",
            message_params={
                "suite": args.suite,
                "passed": report["passed"],
                "total": report["total"],
            },
            data=report,
        ),
        0 if report["all_pass"] else 2,
    )
