"""`rh export --mode draft --format docx|md` (M2-12)."""

from __future__ import annotations

import argparse
from typing import Any

from research_harness.cli.context import object_root
from research_harness.core.envelope import build_envelope
from research_harness.export_docx import assemble


def register(sub: argparse._SubParsersAction) -> None:
    ex = sub.add_parser("export", help="Export a draft (.docx or .md) with references and gaps.")
    ex.add_argument("--mode", default="draft", choices=["draft"])
    ex.add_argument("--format", dest="fmt", default="docx", choices=["docx", "md"])
    ex.add_argument("--pack", default="ua-fahove-b")


def handles(command: str) -> bool:
    return command == "export"


def route(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = object_root(args)
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
