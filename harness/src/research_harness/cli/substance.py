"""`rh substance` — post-draft substance report (ADR-023, M4-15).

Read-only. Lists material claims that are still weak and what to supply, plus an
"analysis-free" warning. Advisory (never blocks); the readiness gate is separate.
"""

from __future__ import annotations

import argparse
from typing import Any

from research_harness.cli.context import object_root
from research_harness.core.envelope import build_envelope
from research_harness.substance import report as report_mod


def register(sub: argparse._SubParsersAction) -> None:
    sub.add_parser("substance", help="Post-draft substance report: weak claims + what to supply.")


def handles(command: str) -> bool:
    return command == "substance"


def route(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = object_root(args)
    findings, data, next_actions = report_mod.build(root)
    return (
        build_envelope(
            command="substance",
            status="partial" if findings else "ok",
            lang=lang,
            message_key="substance.report",
            message_params={"w": data["material_claims_weak"]},
            findings=findings,
            data=data,
            next_actions=next_actions or None,
        ),
        0,
    )
