"""`rh findings list|resolve` and `rh dispute open|add-evidence|close` (M3-05).

Accept / reject of a finding, and closing a dispute as resolved_by_author, are
human-only (the gate channel rule, 02 §9.3): an agent call writes nothing and
returns a resolution request with exit 3 (H14).
"""

from __future__ import annotations

import argparse
from typing import Any

from research_harness.cli.context import object_root
from research_harness.core.envelope import build_envelope
from research_harness.findings import index as findings_mod
from research_harness.gates.interactive import is_human_channel
from research_harness.review import disputes as disputes_mod

_COMMANDS = ("dispute",)


def add_findings_subactions(fia: argparse._SubParsersAction) -> None:
    """Register `list`/`resolve` on the shared `findings` command (owned by the
    synthesis CLI, which delegates these actions here). `findings set` stays with
    synthesis; the command is one namespace (review.md)."""
    fl = fia.add_parser("list", help="List review findings (optionally by status).")
    fl.add_argument("--status", choices=list(findings_mod.STATUSES))
    fr = fia.add_parser("resolve", help="Resolve a finding (human terminal only).")
    fr.add_argument("finding_id")
    fr.add_argument("--decision", required=True, choices=["accept", "reject", "fixed"])
    fr.add_argument("--reason")


def register(sub: argparse._SubParsersAction) -> None:
    dp = sub.add_parser("dispute", help="Analyst/critic disputes over a finding.")
    da = dp.add_subparsers(dest="dispute_action", metavar="action", required=True)
    do = da.add_parser("open", help="Open a dispute on a claim's finding.")
    do.add_argument("--claim", required=True)
    do.add_argument("--finding", required=True)
    do.add_argument(
        "--max-cycles", dest="max_cycles", type=int, default=disputes_mod.DEFAULT_MAX_CYCLES
    )
    de = da.add_parser("add-evidence", help="Add one cycle's argument and evidence.")
    de.add_argument("dispute_id")
    de.add_argument("--by", required=True, choices=["analyst", "critic"])
    de.add_argument("--argument", required=True)
    de.add_argument("--evidence", action="append", default=[], help="Evidence ref; repeatable.")
    dc = da.add_parser("close", help="Close a dispute (resolved_by_author is human-only).")
    dc.add_argument("dispute_id")
    dc.add_argument("--status", required=True, choices=["resolved_by_author", "unresolved"])
    dc.add_argument("--author-decision", dest="author_decision")


def handles(command: str) -> bool:
    return command in _COMMANDS


def route(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = object_root(args)
    if args.dispute_action == "open":
        return _dispute_open(root, args, lang)
    if args.dispute_action == "add-evidence":
        return _dispute_add(root, args, lang)
    return _dispute_close(root, args, lang)


def findings_list(root: Any, args: Any, lang: str) -> tuple[dict[str, Any], int]:
    items = findings_mod.list_findings(root, status=args.status)
    return (
        build_envelope(
            command="findings",
            status="ok",
            lang=lang,
            message_key="findings.listed",
            message_params={"n": len(items)},
            data={"findings": items},
        ),
        0,
    )


def _human_only_request(command: str, lang: str, cmd_hint: str) -> tuple[dict[str, Any], int]:
    return (
        build_envelope(
            command=command,
            status="blocked",
            lang=lang,
            message_key="error.resolution_human_only",
            next_actions=[{"who": "author", "action": cmd_hint}],
        ),
        3,
    )


def findings_resolve(root: Any, args: Any, lang: str) -> tuple[dict[str, Any], int]:
    if not is_human_channel():
        return _human_only_request(
            "findings", lang, f"rh findings resolve {args.finding_id} --decision {args.decision}"
        )
    try:
        entry = findings_mod.resolve(
            root, args.finding_id, decision=args.decision, reason=args.reason, by="author"
        )
    except ValueError as exc:
        return (
            build_envelope(
                command="findings",
                status="invalid",
                lang=lang,
                message_key="error.resolution_invalid",
                message_params={"why": str(exc)},
                data={"error": str(exc)},
            ),
            2,
        )
    except KeyError:
        return (
            build_envelope(
                command="findings",
                status="invalid",
                lang=lang,
                message_key="error.finding_unknown",
                message_params={"id": args.finding_id},
            ),
            2,
        )
    return (
        build_envelope(
            command="findings",
            status="ok",
            lang=lang,
            message_key="findings.resolved",
            message_params={"id": entry["id"], "status": entry["status"]},
            data={"finding": entry},
        ),
        0,
    )


def _dispute_open(root: Any, args: Any, lang: str) -> tuple[dict[str, Any], int]:
    rec = disputes_mod.open_(
        root, claim_id=args.claim, finding_id=args.finding, max_cycles=args.max_cycles
    )
    return (
        build_envelope(
            command="dispute",
            status="ok",
            lang=lang,
            message_key="dispute.opened",
            message_params={"id": rec["id"]},
            data={"dispute": rec},
        ),
        0,
    )


def _dispute_add(root: Any, args: Any, lang: str) -> tuple[dict[str, Any], int]:
    try:
        rec = disputes_mod.add_evidence(
            root, args.dispute_id, by=args.by, argument=args.argument, evidence_refs=args.evidence
        )
    except ValueError as exc:
        return (
            build_envelope(
                command="dispute",
                status="blocked",
                lang=lang,
                message_key="error.dispute_closed_or_capped",
                message_params={"why": str(exc)},
                data={"error": str(exc)},
            ),
            3,
        )
    status = "partial" if disputes_mod.cap_reached(rec) else "ok"
    return (
        build_envelope(
            command="dispute",
            status=status,
            lang=lang,
            message_key="dispute.evidence_added",
            message_params={"id": rec["id"], "cycles": len(rec["cycles"])},
            data={"dispute": rec, "cap_reached": disputes_mod.cap_reached(rec)},
        ),
        0,
    )


def _dispute_close(root: Any, args: Any, lang: str) -> tuple[dict[str, Any], int]:
    if args.status == "resolved_by_author" and not is_human_channel():
        return _human_only_request(
            "dispute", lang, f"rh dispute close {args.dispute_id} --status resolved_by_author"
        )
    rec = disputes_mod.close(
        root, args.dispute_id, status=args.status, author_decision=args.author_decision
    )
    return (
        build_envelope(
            command="dispute",
            status="ok",
            lang=lang,
            message_key="dispute.closed",
            message_params={"id": rec["id"], "status": rec["status"]},
            data={"dispute": rec},
        ),
        0,
    )
