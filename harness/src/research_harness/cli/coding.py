"""`rh coding add|summary` (M3-21, analysis-sandbox.md, FR-54)."""

from __future__ import annotations

import argparse
from typing import Any

from research_harness.analysis import coding
from research_harness.cli.context import object_root
from research_harness.core.envelope import build_envelope

_COMMAND = "coding"


def register(sub: argparse._SubParsersAction) -> None:
    cg = sub.add_parser(_COMMAND, help="Qualitative coding of public documents.")
    sa = cg.add_subparsers(dest="coding_action", metavar="action", required=True)
    add = sa.add_parser("add", help="Code an excerpt (quote verified against the document).")
    add.add_argument("--codebook", required=True)
    add.add_argument("--code", required=True)
    add.add_argument("--document", dest="document_ref", required=True)
    add.add_argument("--quote", required=True)
    add.add_argument("--locator", default="")
    add.add_argument(
        "--doc-file", dest="doc_file", default=None, help="Local document text to verify against."
    )
    sm = sa.add_parser("summary", help="Frequencies and unverified quotes.")
    sm.add_argument("--codebook", required=True)


def handles(command: str) -> bool:
    return command == _COMMAND


def route(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = object_root(args)
    if args.coding_action == "add":
        rec = coding.add_code(
            root,
            codebook=args.codebook,
            code=args.code,
            document_ref=args.document_ref,
            quote=args.quote,
            locator=args.locator,
            doc_file=args.doc_file,
        )
        findings = [] if rec["verified"] else coding.quote_findings(root, args.codebook)[-1:]
        return (
            build_envelope(
                command=_COMMAND,
                status="ok" if rec["verified"] else "partial",
                lang=lang,
                message_key="coding.added" if rec["verified"] else "coding.unverified",
                message_params={"id": rec["id"]},
                findings=findings,
                data={"code": rec},
            ),
            0,
        )
    summary = coding.summary(root, args.codebook)
    findings = coding.quote_findings(root, args.codebook)
    return (
        build_envelope(
            command=_COMMAND,
            status="partial" if findings else "ok",
            lang=lang,
            message_key="coding.summary",
            message_params={"n": summary["total"], "unverified": len(summary["unverified"])},
            findings=findings,
            data=summary,
        ),
        0,
    )
