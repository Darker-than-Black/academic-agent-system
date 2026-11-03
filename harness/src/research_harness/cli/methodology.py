"""`rh methodology set|show|check` — review corpus methodology (ADR-023, M4-17)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from research_harness.cli.context import object_root
from research_harness.core.envelope import build_envelope
from research_harness.methodology import record as record_mod


def register(sub: argparse._SubParsersAction) -> None:
    md = sub.add_parser("methodology", help="Review corpus methodology: search log, criteria.")
    ma = md.add_subparsers(dest="methodology_action", metavar="action", required=True)
    mset = ma.add_parser("set", help="Set the methodology record from a JSON file.")
    mset.add_argument("--file", required=True)
    ma.add_parser("show", help="Show the methodology record and the rendered methods markdown.")
    ma.add_parser("check", help="List reproducible-corpus deficits (search log, criteria, corpus).")


def handles(command: str) -> bool:
    return command == "methodology"


def route(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = object_root(args)
    action = args.methodology_action

    if action == "set":
        data = json.loads(Path(args.file).read_text(encoding="utf-8"))
        stored = record_mod.save(root, data)
        return (
            build_envelope(
                command="methodology",
                status="ok",
                lang=lang,
                message_key="methodology.saved",
                data={"methodology": stored},
            ),
            0,
        )

    if action == "show":
        return (
            build_envelope(
                command="methodology",
                status="ok",
                lang=lang,
                message_key="methodology.shown",
                data={
                    "methodology": record_mod.load(root),
                    "methods_markdown": record_mod.methods_markdown(root),
                },
            ),
            0,
        )

    findings = record_mod.deficits(root)
    seen: set[str] = set()
    next_actions: list[dict[str, Any]] = []
    for f in findings:
        action = f.get("proposed_action", "")
        if action and action not in seen:
            seen.add(action)
            next_actions.append({"who": "author", "action": action})
    return (
        build_envelope(
            command="methodology",
            status="partial" if findings else "ok",
            lang=lang,
            message_key="methodology.checked",
            message_params={"n": len(findings)},
            findings=findings,
            next_actions=next_actions or None,
        ),
        0,
    )
