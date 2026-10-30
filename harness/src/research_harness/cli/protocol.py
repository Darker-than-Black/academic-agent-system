"""`rh protocol draft|show|freeze` (M2-05).

freeze opens the G1 approval request and hands the record step to the author
(H14): the agent never records a gate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from research_harness.cli.context import object_root
from research_harness.core.envelope import build_envelope
from research_harness.i18n import t
from research_harness.lab import protocol as proto_mod


def register(sub: argparse._SubParsersAction) -> None:
    pr = sub.add_parser("protocol", help="Draft, show and freeze the research protocol.")
    pa = pr.add_subparsers(dest="protocol_action", metavar="action", required=True)
    dr = pa.add_parser("draft", help="Draft or re-version the protocol from fields.")
    dr.add_argument("--file", help="YAML/JSON file with protocol fields.")
    pa.add_parser("show", help="Show the latest protocol.")
    pa.add_parser("freeze", help="Freeze the protocol and open the G1 request.")


def handles(command: str) -> bool:
    return command == "protocol"


def _oid(root: Path) -> str:
    return json.loads((root / "object.json").read_text(encoding="utf-8"))["id"]


def route(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = object_root(args)
    action = args.protocol_action
    if action == "draft":
        fields = {}
        if args.file:
            fields = yaml.safe_load(Path(args.file).read_text(encoding="utf-8")) or {}
        proto, findings, discovery = proto_mod.draft(root, fields)
        blocked = any(f["severity"] == "blocker" for f in findings)
        key = "protocol.discovery" if proto["status"] == "discovery" else "protocol.drafted"
        return (
            build_envelope(
                command="protocol",
                status="blocked" if blocked else ("partial" if findings else "ok"),
                lang=lang,
                message_key=key,
                message_params={"v": proto["version"]},
                findings=findings,
                data={"protocol": proto, "discovery_plan": discovery},
            ),
            3 if blocked else 0,
        )
    if action == "show":
        proto = proto_mod.load_latest(root)
        return (
            build_envelope(
                command="protocol",
                status="ok",
                lang=lang,
                message_key="protocol.shown",
                data={"protocol": proto},
            ),
            0,
        )
    # freeze
    proto, ar_id, findings = proto_mod.freeze(root, lang)
    if ar_id is None:
        return (
            build_envelope(
                command="protocol",
                status="blocked",
                lang=lang,
                message_key="protocol.freeze_blocked",
                findings=findings,
                data={"protocol": proto},
            ),
            3,
        )
    briefing = f"approvals/requests/{ar_id}.md"
    command = f"rh --object {_oid(root)} gate record G1"
    return (
        build_envelope(
            command="protocol",
            status="ok",
            lang=lang,
            message_key="protocol.frozen_g1",
            message_params={"ar": ar_id, "briefing": briefing},
            next_actions=[
                {
                    "command": command,
                    "who": "author",
                    "why": t("gate.record_terminal", lang),
                    "briefing": briefing,
                }
            ],
            data={"protocol": proto, "request": ar_id, "briefing_path": briefing},
        ),
        0,
    )
