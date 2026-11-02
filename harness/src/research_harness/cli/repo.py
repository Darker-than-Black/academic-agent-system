"""`rh repo check [--staged]` — repository / PR safety check (M3-14, T41)."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from research_harness.core.envelope import build_envelope
from research_harness.integrity import repo as repo_mod

_COMMAND = "repo"


def register(sub: argparse._SubParsersAction) -> None:
    rp = sub.add_parser(_COMMAND, help="Repository / PR safety checks.")
    sa = rp.add_subparsers(dest="repo_action", metavar="action", required=True)
    chk = sa.add_parser("check", help="Block holdout, secrets and forbidden paths.")
    chk.add_argument("--staged", action="store_true", help="Check staged files only.")


def handles(command: str) -> bool:
    return command == _COMMAND


def route(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    repo_root = repo_mod.git_root(Path.cwd())
    report = repo_mod.run(repo_root, staged=bool(getattr(args, "staged", False)))
    findings = repo_mod.findings_from(report)
    blocked = bool(findings)
    return (
        build_envelope(
            command=_COMMAND,
            status="blocked" if blocked else "ok",
            lang=lang,
            message_key="repo.blocked" if blocked else "repo.clean",
            message_params={"n": len(findings)},
            findings=findings,
            data=report,
        ),
        3 if blocked else 0,
    )
