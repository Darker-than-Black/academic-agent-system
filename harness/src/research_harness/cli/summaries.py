"""`rh summary build|set|check`, `rh map build`, `rh glossary add|check` (M2-08)."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

from research_harness.cli.context import object_root
from research_harness.core.envelope import build_envelope
from research_harness.summaries import deterministic as det_mod
from research_harness.summaries import glossary as glossary_mod
from research_harness.summaries import map as map_mod
from research_harness.summaries import semantic as semantic_mod


def register(sub: argparse._SubParsersAction) -> None:
    su = sub.add_parser("summary", help="Unit summaries: build, set, check.")
    sua = su.add_subparsers(dest="summary_action", metavar="action", required=True)
    sb = sua.add_parser("build")
    sb.add_argument("unit")
    sb.add_argument("--deterministic-only", action="store_true", dest="deterministic_only")
    ss = sua.add_parser("set")
    ss.add_argument("unit")
    ss.add_argument("--file", required=True)
    sua.add_parser("check")

    mp = sub.add_parser("map", help="Document map.")
    mpa = mp.add_subparsers(dest="map_action", metavar="action", required=True)
    mpa.add_parser("build")

    gl = sub.add_parser("glossary", help="Glossary terms and checks.")
    gla = gl.add_subparsers(dest="glossary_action", metavar="action", required=True)
    ga = gla.add_parser("add")
    ga.add_argument("--term", required=True)
    ga.add_argument("--definition", required=True)
    ga.add_argument("--source", required=True)
    ga.add_argument("--alias", action="append", default=[], dest="aliases")
    ga.add_argument("--first-unit", dest="first_unit")
    ga.add_argument("--language", default="uk")
    gla.add_parser("check")


def handles(command: str) -> bool:
    return command in ("summary", "map", "glossary")


def route(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = object_root(args)
    if args.command == "summary":
        return _summary(args, root, lang)
    if args.command == "map":
        report = map_mod.build(root)
        return (
            build_envelope(
                command="map",
                status="ok",
                lang=lang,
                message_key="summary.map_built",
                message_params=report,
                data=report,
            ),
            0,
        )
    return _glossary(args, root, lang)


def _summary(args: Any, root: Path, lang: str) -> tuple[dict[str, Any], int]:
    if args.summary_action == "build":
        summary = det_mod.build_unit(root, args.unit)
        return (
            build_envelope(
                command="summary",
                status="ok",
                lang=lang,
                message_key="summary.built",
                message_params={"unit": args.unit},
                data={"summary": summary},
            ),
            0,
        )
    if args.summary_action == "set":
        data = yaml.safe_load(Path(args.file).read_text(encoding="utf-8")) or {}
        summary, findings = semantic_mod.set_semantic(
            root,
            args.unit,
            main_thesis=data.get("main_thesis", ""),
            key_claims=data.get("key_claims", []),
            open_questions=data.get("open_questions"),
            language=data.get("language", "uk"),
        )
        blocked = any(f["severity"] in ("blocker", "major") for f in findings)
        return (
            build_envelope(
                command="summary",
                status="blocked" if blocked else "ok",
                lang=lang,
                message_key="summary.semantic_set",
                message_params={"unit": args.unit},
                findings=findings,
                data={"summary": summary},
            ),
            3 if blocked else 0,
        )
    # check
    report = map_mod.stale_report(root)
    stale = [k for k, v in report.items() if v]
    findings = [
        {
            "check_id": "summary.stale" if k != "map" else "map.stale",
            "severity": "blocker",
            "reason": f"{k} is stale",
            "location": {},
            "proposed_action": "",
        }
        for k in stale
    ]
    blocked = bool(findings)
    return (
        build_envelope(
            command="summary",
            status="blocked" if blocked else "ok",
            lang=lang,
            message_key="summary.checked",
            findings=findings,
            data={"stale": report},
        ),
        3 if blocked else 0,
    )


def _glossary(args: Any, root: Path, lang: str) -> tuple[dict[str, Any], int]:
    if args.glossary_action == "add":
        entry = glossary_mod.add_term(
            root,
            term=args.term,
            definition=args.definition,
            source=args.source,
            aliases=args.aliases,
            first_unit=args.first_unit,
            language=args.language,
        )
        return (
            build_envelope(
                command="glossary",
                status="ok",
                lang=lang,
                message_key="glossary.added",
                message_params={"term": args.term},
                data={"term": entry},
            ),
            0,
        )
    findings = glossary_mod.check(root)
    return (
        build_envelope(
            command="glossary",
            status="partial" if findings else "ok",
            lang=lang,
            message_key="glossary.checked",
            findings=findings,
        ),
        0,
    )
