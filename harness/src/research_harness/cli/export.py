"""`rh export --mode draft|verified --format docx|md` (M2-12 draft, M3-15 verified).

A verified export re-checks every FR-12 condition in code and refuses (exit 3)
when any is open; it never trusts a cached PASS (integrity.md invariant 4)."""

from __future__ import annotations

import argparse
from typing import Any

from research_harness.cli.context import object_root
from research_harness.core.envelope import build_envelope
from research_harness.export_docx import assemble
from research_harness.integrity import verified


def register(sub: argparse._SubParsersAction) -> None:
    ex = sub.add_parser("export", help="Export a draft or verified bundle with references.")
    ex.add_argument("--mode", default="draft", choices=["draft", "verified"])
    ex.add_argument("--format", dest="fmt", default="docx", choices=["docx", "md"])
    ex.add_argument("--pack", default="ua-fahove-b")


def handles(command: str) -> bool:
    return command == "export"


def route(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = object_root(args)
    if args.mode == "verified":
        return _verified(root, args, lang)
    result = assemble.export_draft(root, fmt=args.fmt, pack=args.pack)
    status = "partial" if result["gaps"] else "ok"
    return (
        build_envelope(
            command="export",
            status=status,
            lang=lang,
            message_key="export.done",
            message_params={"format": result["format"], "gaps": len(result["gaps"])},
            findings=result["gaps"],
            data=result,
        ),
        0,
    )


def _verified(root: Any, args: Any, lang: str) -> tuple[dict[str, Any], int]:
    findings = verified.check_conditions(root, pack=args.pack)
    if findings:
        return (
            build_envelope(
                command="export",
                status="blocked",
                lang=lang,
                message_key="export.verified_blocked",
                message_params={"n": len(findings)},
                findings=findings,
            ),
            3,
        )
    result = assemble.export_verified(root, fmt=args.fmt, pack=args.pack)
    return (
        build_envelope(
            command="export",
            status="ok",
            lang=lang,
            message_key="export.verified_done",
            message_params={"format": result["format"], "snapshot": result["snapshot_id"]},
            data=result,
        ),
        0,
    )
