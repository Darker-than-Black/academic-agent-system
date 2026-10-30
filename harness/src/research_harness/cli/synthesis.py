"""Synthesis desk CLI (M2-04):
rh excerpt add | rh matrix add | rh premise add | rh positions set |
rh gaps set | rh counter-evidence record | rh saturation check | rh findings set.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

from research_harness.cli.context import object_root
from research_harness.core.envelope import build_envelope
from research_harness.evidence import excerpts as excerpts_mod
from research_harness.evidence import premises as premises_mod
from research_harness.lab import counter as counter_mod
from research_harness.lab import findings as findings_mod
from research_harness.lab import gaps as gaps_mod
from research_harness.lab import matrix as matrix_mod
from research_harness.lab import positions as positions_mod
from research_harness.lab import saturation as saturation_mod

_ACCESS = ["metadata", "abstract", "fulltext", "local_original"]
_METHOD = ["manual", "pdf_text", "ocr", "api_abstract"]


def register(sub: argparse._SubParsersAction) -> None:
    ex = sub.add_parser("excerpt", help="Add an excerpt (runs the quote check).")
    exa = ex.add_subparsers(dest="excerpt_action", metavar="action", required=True)
    add = exa.add_parser("add")
    add.add_argument("--source", required=True)
    add.add_argument("--text", required=True)
    add.add_argument("--pdf-page", type=int, dest="pdf_page")
    add.add_argument("--printed-page", dest="printed_page")
    add.add_argument("--section")
    add.add_argument("--paragraph")
    add.add_argument("--access", required=True, choices=_ACCESS)
    add.add_argument("--method", default="manual", choices=_METHOD)

    mx = sub.add_parser("matrix", help="Add an extraction-matrix row.")
    mxa = mx.add_subparsers(dest="matrix_action", metavar="action", required=True)
    madd = mxa.add_parser("add")
    madd.add_argument("--source", required=True)
    madd.add_argument("--question", required=True)
    madd.add_argument("--statement", required=True)
    madd.add_argument("--data-basis", dest="data_basis", default="")
    madd.add_argument("--limitations", default="")
    madd.add_argument("--excerpt", action="append", default=[], dest="excerpts")
    madd.add_argument("--position")

    pr = sub.add_parser("premise", help="Add a premise or definition.")
    pra = pr.add_subparsers(dest="premise_action", metavar="action", required=True)
    padd = pra.add_parser("add")
    padd.add_argument("--statement", required=True)
    padd.add_argument("--kind", default="premise", choices=["premise", "definition"])
    padd.add_argument("--term")
    padd.add_argument("--excerpt", action="append", default=[], dest="excerpts")
    padd.add_argument("--assumption", action="store_true")

    po = sub.add_parser("positions", help="Set the position map from a file.")
    poa = po.add_subparsers(dest="positions_action", metavar="action", required=True)
    poa.add_parser("set").add_argument("--file", required=True)

    gp = sub.add_parser("gaps", help="Set research gaps from a file.")
    gpa = gp.add_subparsers(dest="gaps_action", metavar="action", required=True)
    gpa.add_parser("set").add_argument("--file", required=True)

    ce = sub.add_parser("counter-evidence", help="Record counter-evidence for a claim.")
    cea = ce.add_subparsers(dest="counter_action", metavar="action", required=True)
    crec = cea.add_parser("record")
    crec.add_argument("--claim", required=True)
    crec.add_argument("--query", action="append", default=[], dest="queries")
    crec.add_argument("--outcome", required=True, choices=list(counter_mod.OUTCOMES))
    crec.add_argument("--note")

    sa = sub.add_parser("saturation", help="Check saturation from matrix rows.")
    saa = sa.add_subparsers(dest="saturation_action", metavar="action", required=True)
    scheck = saa.add_parser("check")
    scheck.add_argument("--batch-size", type=int, default=10, dest="batch_size")

    fi = sub.add_parser("findings", help="Hand synthesis findings to the writer.")
    fia = fi.add_subparsers(dest="findings_action", metavar="action", required=True)
    fset = fia.add_parser("set")
    fset.add_argument("--file", required=True)
    fset.add_argument("--central", action="append", default=[], dest="central")


_COMMANDS = (
    "excerpt",
    "matrix",
    "premise",
    "positions",
    "gaps",
    "counter-evidence",
    "saturation",
    "findings",
)


def handles(command: str) -> bool:
    return command in _COMMANDS


def _env(cmd, lang, key, *, params=None, findings=None, data=None, blocked=False):
    status = "blocked" if blocked else ("partial" if findings else "ok")
    return (
        build_envelope(
            command=cmd,
            status=status,
            lang=lang,
            message_key=key,
            message_params=params,
            findings=findings,
            data=data or {},
        ),
        3 if blocked else 0,
    )


def route(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = object_root(args)
    cmd = args.command
    if cmd == "excerpt":
        locator = {
            "pdf_page": args.pdf_page,
            "printed_page": args.printed_page,
            "section": args.section,
            "paragraph": args.paragraph,
        }
        exc, findings = excerpts_mod.add_excerpt(
            root,
            source_id=args.source,
            text=args.text,
            locator=locator,
            access_level=args.access,
            extraction_method=args.method,
        )
        return _env(
            "excerpt",
            lang,
            "synth.excerpt_added",
            params={"id": exc["id"], "result": exc["quote_check"]["result"]},
            findings=findings,
            data={"excerpt": exc},
        )
    if cmd == "matrix":
        row, findings = matrix_mod.add_row(
            root,
            source_id=args.source,
            question_id=args.question,
            statement=args.statement,
            data_basis=args.data_basis,
            limitations=args.limitations,
            excerpt_ids=args.excerpts,
            position=args.position,
        )
        return _env(
            "matrix",
            lang,
            "synth.matrix_added",
            params={"id": row["id"]},
            findings=findings,
            data={"row": row},
        )
    if cmd == "premise":
        pre, findings = premises_mod.add_premise(
            root,
            statement=args.statement,
            kind=args.kind,
            term=args.term,
            excerpt_ids=args.excerpts,
            assumption=args.assumption,
        )
        if pre is None:
            return _env("premise", lang, "synth.premise_rejected", findings=findings, blocked=True)
        return _env(
            "premise", lang, "synth.premise_added", params={"id": pre["id"]}, data={"premise": pre}
        )
    if cmd == "positions":
        items = yaml.safe_load(Path(args.file).read_text(encoding="utf-8")) or []
        items = items.get("positions", items) if isinstance(items, dict) else items
        findings = positions_mod.set_positions(root, items)
        return _env(
            "positions",
            lang,
            "synth.positions_set",
            params={"n": len(items)},
            findings=findings,
            blocked=bool(findings),
        )
    if cmd == "gaps":
        items = yaml.safe_load(Path(args.file).read_text(encoding="utf-8")) or []
        items = items.get("gaps", items) if isinstance(items, dict) else items
        findings = gaps_mod.set_gaps(root, items)
        return _env(
            "gaps",
            lang,
            "synth.gaps_set",
            params={"n": len(items)},
            findings=findings,
            blocked=bool(findings),
        )
    if cmd == "counter-evidence":
        entry, findings = counter_mod.record(
            root, claim_ref=args.claim, queries=args.queries, outcome=args.outcome, note=args.note
        )
        if entry is None:
            return _env(
                "counter-evidence", lang, "synth.counter_blocked", findings=findings, blocked=True
            )
        return _env(
            "counter-evidence",
            lang,
            "synth.counter_recorded",
            params={"claim": args.claim, "outcome": args.outcome},
            data={"record": entry},
        )
    if cmd == "saturation":
        report = saturation_mod.check(root, batch_size=args.batch_size)
        key = "synth.saturation_stop" if report["propose_stop"] else "synth.saturation_cont"
        return _env(
            "saturation",
            lang,
            key,
            params={"themes": report["total_themes"]},
            data={"saturation": report},
        )
    # findings
    items = yaml.safe_load(Path(args.file).read_text(encoding="utf-8")) or []
    items = items.get("findings", items) if isinstance(items, dict) else items
    findings = findings_mod.set_findings(root, items, central_claims=args.central)
    if findings:
        return _env("findings", lang, "synth.findings_blocked", findings=findings, blocked=True)
    return _env("findings", lang, "synth.findings_set", params={"n": len(items)})
