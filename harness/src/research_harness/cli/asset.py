"""`rh asset add|list` — asset registry (M3-12, FR-17)."""

from __future__ import annotations

import argparse
from typing import Any

from research_harness.cli.context import object_root
from research_harness.core.envelope import build_envelope
from research_harness.integrity import assets as assets_mod

_COMMAND = "asset"


def register(sub: argparse._SubParsersAction) -> None:
    ap = sub.add_parser(_COMMAND, help="Asset registry (figures, tables, images).")
    sa = ap.add_subparsers(dest="asset_action", metavar="action", required=True)
    add = sa.add_parser("add", help="Register an asset with its origin and rights.")
    add.add_argument("path", help="Asset path relative to the object folder.")
    add.add_argument(
        "--origin", required=True, choices=["own_generated", "own_data", "third_party"]
    )
    add.add_argument(
        "--rights",
        required=True,
        dest="rights",
        choices=["own", "licensed", "permission_documented", "unknown"],
    )
    add.add_argument("--kind", default="other", choices=["figure", "table", "image", "other"])
    add.add_argument("--license", default=None)
    add.add_argument("--source-ref", dest="source_ref", default=None)
    add.add_argument("--permission-doc", dest="permission_doc", default=None)
    add.add_argument(
        "--from-rows",
        dest="from_rows",
        default=None,
        help="Comma-separated result-row ids for own_generated figures.",
    )
    sa.add_parser("list", help="List registered assets.")


def handles(command: str) -> bool:
    return command == _COMMAND


def route(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = object_root(args)
    if args.asset_action == "list":
        items = assets_mod.load(root)
        return (
            build_envelope(
                command=_COMMAND,
                status="ok",
                lang=lang,
                message_key="asset.listed",
                message_params={"n": len(items)},
                data={"assets": items},
            ),
            0,
        )
    rows = [r.strip() for r in args.from_rows.split(",")] if args.from_rows else None
    rec = assets_mod.add_asset(
        root,
        args.path,
        origin=args.origin,
        rights_status=args.rights,
        kind=args.kind,
        license=args.license,
        source_ref=args.source_ref,
        permission_doc_path=args.permission_doc,
        generated_from_rows=rows,
    )
    return (
        build_envelope(
            command=_COMMAND,
            status="ok",
            lang=lang,
            message_key="asset.added",
            message_params={"id": rec["id"]},
            data={"asset": rec},
        ),
        0,
    )
