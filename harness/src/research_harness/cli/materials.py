"""`rh materials add|list` (M1-09)."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from research_harness.cli.context import object_root
from research_harness.core.envelope import build_envelope
from research_harness.materials import manifest

_COMMAND = "materials"


def register(sub: argparse._SubParsersAction) -> None:
    mt = sub.add_parser(_COMMAND, help="Materials manifest.")
    sa = mt.add_subparsers(dest="materials_action", metavar="action", required=True)
    add = sa.add_parser("add", help="Register a material.")
    g = add.add_mutually_exclusive_group(required=True)
    g.add_argument("--file")
    g.add_argument("--bibtex")
    g.add_argument("--ris")
    g.add_argument("--doi-list", dest="doi_list")
    add.add_argument("--kind", default="file")
    add.add_argument("--private", action="store_true")
    sa.add_parser("list", help="List registered materials.")


def handles(command: str) -> bool:
    return command == _COMMAND


def route(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = object_root(args)
    if args.materials_action == "list":
        data = manifest.load(root)
        return (
            build_envelope(
                command=_COMMAND,
                status="ok",
                lang=lang,
                message_key="materials.listed",
                message_params={"n": len(data["materials"])},
                data={"materials": data["materials"]},
            ),
            0,
        )

    findings: list[dict[str, Any]] = []
    if args.file:
        entry = manifest.add_file(root, Path(args.file), kind=args.kind, private=args.private)
    elif args.bibtex:
        entry, findings = manifest.add_bibtex(root, Path(args.bibtex))
    elif args.ris:
        entry, findings = manifest.add_ris(root, Path(args.ris))
    else:
        entry, findings = manifest.add_doi_list(root, Path(args.doi_list))
    return (
        build_envelope(
            command=_COMMAND,
            status="partial" if findings else "ok",
            lang=lang,
            message_key="materials.added",
            message_params={"id": entry["id"]},
            findings=findings,
            data={"material": entry},
        ),
        0,
    )
