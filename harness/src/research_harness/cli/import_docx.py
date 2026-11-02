"""`rh import docx FILE [--from supervisor|editor|author] [--actor-label L]`
(M3-09, docx.md). Parse a reviewed ``.docx``, map every tracked change and
comment to a unit, record it, and enter revise mode. Unmapped changes block
until resolved (T46); nothing is written to the manuscript here (H13)."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from research_harness.cli.context import object_root
from research_harness.core.envelope import build_envelope
from research_harness.import_docx import apply


def register(sub: argparse._SubParsersAction) -> None:
    im = sub.add_parser("import", help="Import a reviewed .docx (tracked changes and comments).")
    sa = im.add_subparsers(dest="import_kind", metavar="kind", required=True)
    dx = sa.add_parser("docx", help="Import tracked changes and comments from a .docx.")
    dx.add_argument("file", help="The reviewed .docx file.")
    dx.add_argument(
        "--from",
        dest="source",
        default="editor",
        choices=["supervisor", "editor", "author"],
        help="Who the reviewed file is from (sets change provenance).",
    )
    dx.add_argument("--actor-label", dest="actor_label", default=None)


def handles(command: str) -> bool:
    return command == "import"


def route(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = object_root(args)
    src = root / args.file if (root / args.file).is_file() else Path(args.file)
    result = apply.import_docx(root, src, source=args.source, actor_label=args.actor_label)
    blocked = result["blocked"]
    return (
        build_envelope(
            command="import",
            status="blocked" if blocked else "ok",
            lang=lang,
            message_key="import.blocked" if blocked else "import.done",
            message_params={
                "count": result["count"],
                "mapped": result["mapped"],
                "unmapped": result["unmapped"],
            },
            findings=result["findings"],
            data=result,
            next_actions=[
                {
                    "who": "author",
                    "action": "Review history/imports/<ts>/diff.md; lock units outside "
                    "the revise scope (rh lock U --reason …), then accept changes.",
                }
            ],
        ),
        3 if blocked else 0,
    )
