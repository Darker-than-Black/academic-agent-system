"""`rh ai-use show` / `rh ai-use statement --lang L` (M3-11, integrity.md).

The record and statement are built only from the model-call log and paragraph
provenance (FR-32, invariant 2). A request to conceal AI use is reported, never
applied (N4)."""

from __future__ import annotations

import argparse
from typing import Any

from research_harness.cli.context import main_language, object_root
from research_harness.core.envelope import build_envelope
from research_harness.integrity import ai_use

_COMMAND = "ai-use"


def register(sub: argparse._SubParsersAction) -> None:
    au = sub.add_parser(_COMMAND, help="AI-use record and draft statement (from provenance).")
    sa = au.add_subparsers(dest="ai_use_action", metavar="action", required=True)
    sa.add_parser("show", help="Build and show the AI-use record.")
    st = sa.add_parser("statement", help="Draft the AI-use statement in a language.")
    st.add_argument("--lang", default=None, help="Statement language (default: object language).")


def handles(command: str) -> bool:
    return command == _COMMAND


def route(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = object_root(args)
    if args.ai_use_action == "show":
        record = ai_use.build_record(root)
        ai_use.write_record(root, record)
        findings = ai_use.concealment_findings(root)
        status = "partial" if findings else "ok"
        return (
            build_envelope(
                command=_COMMAND,
                status=status,
                lang=lang,
                message_key="ai_use.shown",
                message_params={"entries": len(record["entries"])},
                findings=findings,
                data=record,
            ),
            0,
        )

    out_lang = args.lang or main_language(root)
    text = ai_use.build_statement(root, out_lang)
    path = ai_use.statement_path(root, out_lang)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return (
        build_envelope(
            command=_COMMAND,
            status="ok",
            lang=lang,
            message_key="ai_use.statement",
            message_params={"lang": out_lang},
            data={"path": str(path.relative_to(root)), "text": text},
            next_actions=[
                {
                    "who": "author",
                    "action": "Review and confirm the draft AI-use statement before submission.",
                }
            ],
        ),
        0,
    )
