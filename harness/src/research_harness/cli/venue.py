"""`rh venue check` — record venue-status evidence (M3-12, FR-37)."""

from __future__ import annotations

import argparse
from typing import Any

from research_harness.cli.context import object_root
from research_harness.core.clock import default_clock
from research_harness.core.envelope import build_envelope
from research_harness.core.hashing import compute_sha256
from research_harness.integrity import venue as venue_mod

_COMMAND = "venue"


def register(sub: argparse._SubParsersAction) -> None:
    vp = sub.add_parser(_COMMAND, help="Target-venue status checks.")
    sa = vp.add_subparsers(dest="venue_action", metavar="action", required=True)
    chk = sa.add_parser("check", help="Record venue-status evidence on a date.")
    chk.add_argument("--title", required=True, help="Venue title.")
    chk.add_argument("--issn", action="append", default=None, help="ISSN (repeatable).")
    chk.add_argument(
        "--resource",
        required=True,
        choices=["scopus_sources", "mjl", "doaj", "ua_perelik", "journal_site"],
    )
    chk.add_argument("--date", default=None, help="Date that matters (default: today).")
    chk.add_argument(
        "--status", required=True, dest="status", choices=["included", "not_included", "unknown"]
    )
    chk.add_argument("--evidence", default=None, help="Evidence URL or file path.")
    chk.add_argument("--checked-by", dest="checked_by", default="author")
    chk.add_argument("--rule-refs", dest="rule_refs", default=None)


def handles(command: str) -> bool:
    return command == _COMMAND


def route(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = object_root(args)
    date = args.date or default_clock().now_rfc3339()[:10]
    evidence: dict[str, Any] = {}
    if args.evidence:
        if args.evidence.startswith(("http://", "https://")):
            evidence["url"] = args.evidence
        else:
            evidence["file"] = args.evidence
            f = root / args.evidence
            if f.is_file():
                evidence["sha256"] = compute_sha256(f)
    refs = [r.strip() for r in args.rule_refs.split(",")] if args.rule_refs else None
    rec = venue_mod.record_check(
        root,
        title=args.title,
        resource=args.resource,
        query_date=date,
        status_value=args.status,
        status_date=date,
        checked_by=args.checked_by,
        issn=args.issn,
        evidence=evidence,
        rule_refs=refs,
    )
    return (
        build_envelope(
            command=_COMMAND,
            status="ok",
            lang=lang,
            message_key="venue.recorded",
            message_params={"id": rec["id"], "value": args.status},
            data={"venue_check": rec},
        ),
        0,
    )
