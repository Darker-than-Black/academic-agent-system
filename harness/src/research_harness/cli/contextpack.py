"""`rh context pack` (M2-09). The CLI context-resolution helper lives in
cli/context.py; this module is the `context` command group."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from research_harness.cli.context import object_root
from research_harness.context import pack as pack_mod
from research_harness.core.envelope import build_envelope


def register(sub: argparse._SubParsersAction) -> None:
    cx = sub.add_parser("context", help="Build a context pack for an agent role.")
    cxa = cx.add_subparsers(dest="context_action", metavar="action", required=True)
    p = cxa.add_parser("pack")
    p.add_argument("target")
    p.add_argument(
        "--role",
        required=True,
        choices=["writer", "unit_critic", "summarizer", "orchestrator", "analyst"],
    )
    p.add_argument("--budget", type=int)
    p.add_argument("--out")


def handles(command: str) -> bool:
    return command == "context"


def route(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = object_root(args)
    manifest, findings = pack_mod.build_pack(root, args.target, args.role, budget=args.budget)
    blocked = any(f["severity"] == "blocker" for f in findings)
    if args.out and not blocked:
        Path(args.out).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    key = (
        "context.refused"
        if manifest.get("refused")
        else ("context.over_budget" if blocked else "context.packed")
    )
    return (
        build_envelope(
            command="context",
            status="blocked" if blocked else "ok",
            lang=lang,
            message_key=key,
            message_params={
                "id": manifest["id"],
                "n": len(manifest["items"]),
                "t": manifest["total_tokens"],
            },
            findings=findings,
            data={"pack": manifest},
        ),
        3 if blocked else 0,
    )
