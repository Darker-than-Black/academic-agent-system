"""`rh claims set|check|coverage` (M2-06)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from research_harness.claims import ledger as ledger_mod
from research_harness.cli.context import object_root
from research_harness.core.envelope import build_envelope


def register(sub: argparse._SubParsersAction) -> None:
    cl = sub.add_parser("claims", help="Claim ledger: set, check, coverage.")
    ca = cl.add_subparsers(dest="claims_action", metavar="action", required=True)
    cset = ca.add_parser("set", help="Set a unit's claims from a file.")
    cset.add_argument("unit")
    cset.add_argument("--file", required=True)
    cchk = ca.add_parser("check", help="Recompute caps for claims (one unit or all).")
    cchk.add_argument("unit", nargs="?")
    ca.add_parser("coverage", help="Coverage with denominator = all material claims.")


def handles(command: str) -> bool:
    return command == "claims"


def route(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = object_root(args)
    action = args.claims_action
    if action == "set":
        claims = json.loads(Path(args.file).read_text(encoding="utf-8"))
        if isinstance(claims, dict):
            claims = claims.get("claims", [])
        stored, findings = ledger_mod.set_claims(root, args.unit, claims)
        blocked = any(f["severity"] == "blocker" for f in findings)
        return (
            build_envelope(
                command="claims",
                status="blocked" if blocked else ("partial" if findings else "ok"),
                lang=lang,
                message_key="claims.set",
                message_params={"n": len(stored)},
                findings=findings,
                data={"claims": stored},
            ),
            3 if blocked else 0,
        )
    if action == "check":
        findings, claims = ledger_mod.check_claims(root, args.unit)
        blocked = any(f["severity"] == "blocker" for f in findings)
        return (
            build_envelope(
                command="claims",
                status="blocked" if blocked else ("partial" if findings else "ok"),
                lang=lang,
                message_key="claims.checked",
                message_params={"n": len(claims)},
                findings=findings,
                data={"coverage": ledger_mod.coverage(root)},
            ),
            3 if blocked else 0,
        )
    cov = ledger_mod.coverage(root)
    return (
        build_envelope(
            command="claims",
            status="ok",
            lang=lang,
            message_key="claims.coverage",
            message_params={"d": cov["denominator"]},
            data={"coverage": cov},
        ),
        0,
    )
