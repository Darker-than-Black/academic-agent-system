"""`rh dataset add … / rh dataset list` (M3-18, analysis-sandbox.md, FR-57)."""

from __future__ import annotations

import argparse
from typing import Any

from research_harness.analysis import datasets
from research_harness.cli.context import object_root
from research_harness.core.envelope import build_envelope

_COMMAND = "dataset"


def register(sub: argparse._SubParsersAction) -> None:
    ds = sub.add_parser(_COMMAND, help="Dataset registry (terms required; download only here).")
    sa = ds.add_subparsers(dest="dataset_action", metavar="action", required=True)
    add = sa.add_parser("add", help="Register a dataset with its terms of use.")
    add.add_argument("--name", required=True)
    add.add_argument("--version", required=True)
    add.add_argument("--url", default=None)
    add.add_argument("--terms", default=None, help="Terms of use: a local FILE or a URL/text.")
    add.add_argument("--from", dest="from_path", default=None, help="Local data file to copy in.")
    add.add_argument("--no-copy", dest="no_copy", action="store_true")
    add.add_argument("--synthetic", action="store_true")
    sa.add_parser("list", help="List registered datasets.")


def handles(command: str) -> bool:
    return command == _COMMAND


def route(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = object_root(args)
    if args.dataset_action == "add":
        rec = datasets.add(
            root,
            name=args.name,
            version=args.version,
            url=args.url,
            terms=args.terms,
            from_path=args.from_path,
            no_copy=args.no_copy,
            synthetic=args.synthetic,
        )
        findings = datasets.terms_findings(root, [rec["id"]])
        return (
            build_envelope(
                command=_COMMAND,
                status="partial" if findings else "ok",
                lang=lang,
                message_key="dataset.added",
                message_params={"id": rec["id"], "name": rec["name"]},
                findings=findings,
                data={"dataset": rec},
            ),
            0,
        )
    items = datasets.load(root)
    return (
        build_envelope(
            command=_COMMAND,
            status="ok",
            lang=lang,
            message_key="dataset.list",
            message_params={"n": len(items)},
            data={"datasets": items},
        ),
        0,
    )
