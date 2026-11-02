"""`rh review prepare|submit`, `rh review integration` (M2-11, v0)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from research_harness.cli.context import object_root
from research_harness.core.envelope import build_envelope
from research_harness.review import fulltext as fulltext_mod
from research_harness.review import handoff as handoff_mod
from research_harness.review import integration_v0
from research_harness.review import numbers as numbers_mod
from research_harness.review import verdicts as verdicts_mod
from research_harness.validate.framework import has_blocker


def register(sub: argparse._SubParsersAction) -> None:
    rv = sub.add_parser("review", help="Review v0: prepare, submit, integration check.")
    rva = rv.add_subparsers(dest="review_action", metavar="action", required=True)
    pr = rva.add_parser("prepare")
    pr.add_argument("--level", required=True, choices=["unit", "article"])
    pr.add_argument("--unit")
    pr.add_argument("--engine", default="claude", choices=["claude", "codex"])
    su = rva.add_parser("submit")
    su.add_argument("review_id")
    su.add_argument("--findings")
    su.add_argument("--verdicts")
    ic = rva.add_parser("integration")
    ic.add_argument("--coverage-unit", dest="coverage_unit")
    cv = rva.add_parser(
        "coverage", help="Coverage of material claims by verdict (full denominator)."
    )
    cv.add_argument("--unit", required=True)
    nm = rva.add_parser("numbers", help="Numbers in a unit's claims vs their cited excerpts.")
    nm.add_argument("--unit", required=True)
    rva.add_parser(
        "fulltext", help="Document-wide deterministic checks (crossref, cites, repeats)."
    )


def handles(command: str) -> bool:
    return command == "review"


def route(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = object_root(args)
    if args.review_action == "prepare":
        from research_harness.review import engine as engine_mod

        requested = getattr(args, "engine", "claude")
        rec = handoff_mod.prepare(root, args.level, unit=args.unit, engine=requested)
        # Codex requested but disabled by config → refuse with an explanation.
        if rec["engine_status"] == engine_mod.DISABLED:
            return (
                build_envelope(
                    command="review",
                    status="blocked",
                    lang=lang,
                    message_key="review.engine_disabled",
                    message_params={"reason": rec["engine_reason"]},
                    data={"handoff": rec},
                ),
                3,
            )
        status = "partial" if rec["engine_status"] != engine_mod.OK else "ok"
        return (
            build_envelope(
                command="review",
                status=status,
                lang=lang,
                message_key="review.prepared",
                message_params={
                    "id": rec["id"],
                    "level": args.level,
                    "engine": rec["engine"],
                    "engine_status": rec["engine_status"],
                },
                data={"handoff": rec},
            ),
            0,
        )
    if args.review_action == "coverage":
        cov = verdicts_mod.coverage(root, args.unit)
        cf = verdicts_mod.coverage_findings(cov)
        return (
            build_envelope(
                command="review",
                status="ok" if cov["status"] == "ok" else "partial",
                lang=lang,
                message_key="review.coverage",
                message_params={"checked": cov["checked"], "denominator": cov["denominator"]},
                findings=cf,
                data={"coverage": cov},
            ),
            0,
        )
    if args.review_action == "fulltext":
        findings = fulltext_mod.run(root)
        blocked = has_blocker(findings)
        return (
            build_envelope(
                command="review",
                status="blocked" if blocked else ("partial" if findings else "ok"),
                lang=lang,
                message_key="review.fulltext",
                message_params={"n": len(findings)},
                findings=findings,
                data={"findings": findings},
            ),
            3 if blocked else 0,
        )
    if args.review_action == "numbers":
        findings = numbers_mod.check_unit_numbers(root, args.unit)
        return (
            build_envelope(
                command="review",
                status="partial" if findings else "ok",
                lang=lang,
                message_key="review.numbers",
                message_params={"n": len(findings)},
                findings=findings,
                data={"findings": findings},
            ),
            0,
        )
    if args.review_action == "submit":
        verdicts = _load(args.verdicts)
        findings = _load(args.findings)
        handoff, problems = verdicts_mod.submit(
            root, args.review_id, verdicts=verdicts, findings=findings
        )
        blocked = bool(problems)
        cov = None
        cov_findings: list[dict[str, Any]] = []
        if handoff["level"] == "unit":
            cov = verdicts_mod.coverage(root, handoff["target"])
            if not blocked:
                cov_findings = verdicts_mod.coverage_findings(cov)
        return (
            build_envelope(
                command="review",
                status="blocked" if blocked else "ok",
                lang=lang,
                message_key="review.submitted" if not blocked else "review.rejected",
                message_params={"id": args.review_id},
                findings=problems if blocked else cov_findings,
                data={"handoff": handoff, "coverage": cov},
            ),
            3 if blocked else 0,
        )
    # integration (deterministic part)
    findings = integration_v0.check(root)
    data: dict[str, Any] = {"findings": findings}
    if args.coverage_unit:
        data["coverage"] = verdicts_mod.coverage(root, args.coverage_unit)
    return (
        build_envelope(
            command="review",
            status="partial" if findings else "ok",
            lang=lang,
            message_key="review.integration",
            findings=findings,
            data=data,
        ),
        0,
    )


def _load(path: str | None) -> list[dict[str, Any]]:
    if not path:
        return []
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data if isinstance(data, list) else data.get("items", [])
