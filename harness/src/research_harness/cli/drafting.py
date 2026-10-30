"""`rh unit diff|write`, `rh dictation import|accept`, `rh provenance show|mark` (M2-10)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from research_harness.cli.context import object_root
from research_harness.core.envelope import build_envelope
from research_harness.provenance import dictation as dict_mod
from research_harness.provenance import paragraphs as prov_mod
from research_harness.units import write as write_mod


def register(sub: argparse._SubParsersAction) -> None:
    un = sub.add_parser("unit", help="Unit drafting: diff preview and requested write.")
    una = un.add_subparsers(dest="unit_action", metavar="action", required=True)
    ud = una.add_parser("diff")
    ud.add_argument("unit")
    ud.add_argument("--file", required=True)
    uw = una.add_parser("write")
    uw.add_argument("unit")
    uw.add_argument("--file", required=True)
    uw.add_argument("--request", required=True)  # missing -> argparse exit 2
    uw.add_argument("--base-file", dest="base_file")

    di = sub.add_parser("dictation", help="Dictation import and structuring.")
    dia = di.add_subparsers(dest="dictation_action", metavar="action", required=True)
    dimp = dia.add_parser("import")
    dimp.add_argument("unit")
    dimp.add_argument("--file", required=True)
    dimp.add_argument("--audio-ref", dest="audio_ref")
    dacc = dia.add_parser("accept")
    dacc.add_argument("unit")
    dacc.add_argument("--file", required=True)
    dacc.add_argument("--raw-file", dest="raw_file")

    pv = sub.add_parser("provenance", help="Paragraph provenance.")
    pva = pv.add_subparsers(dest="provenance_action", metavar="action", required=True)
    ps = pva.add_parser("show")
    ps.add_argument("unit", nargs="?")
    pm = pva.add_parser("mark")
    pm.add_argument("unit")
    pm.add_argument("--paragraph", required=True)
    pm.add_argument("--origin", required=True, choices=list(prov_mod.ORIGINS))


def handles(command: str) -> bool:
    return command in ("unit", "dictation", "provenance")


def route(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = object_root(args)
    if args.command == "unit":
        return _unit(args, root, lang)
    if args.command == "dictation":
        return _dictation(args, root, lang)
    return _provenance(args, root, lang)


def _unit(args: Any, root: Path, lang: str) -> tuple[dict[str, Any], int]:
    body = Path(args.file).read_text(encoding="utf-8")
    if args.unit_action == "diff":
        d = write_mod.diff_preview(root, args.unit, body)
        return (
            build_envelope(
                command="unit", status="ok", lang=lang, message_key="draft.diff", data={"diff": d}
            ),
            0,
        )
    base = None
    if args.base_file:
        base = json.loads(Path(args.base_file).read_text(encoding="utf-8"))
    paras, _ = write_mod.write_unit(root, args.unit, body, request=args.request, base=base)
    return (
        build_envelope(
            command="unit",
            status="ok",
            lang=lang,
            message_key="draft.written",
            message_params={"unit": args.unit, "n": len(paras)},
            data={"paragraphs": paras},
        ),
        0,
    )


def _dictation(args: Any, root: Path, lang: str) -> tuple[dict[str, Any], int]:
    if args.dictation_action == "import":
        transcript = Path(args.file).read_text(encoding="utf-8")
        result = dict_mod.import_transcript(root, args.unit, transcript, audio_ref=args.audio_ref)
        return (
            build_envelope(
                command="dictation",
                status="ok",
                lang=lang,
                message_key="draft.dictation_imported",
                message_params={"unit": args.unit},
                data=result,
            ),
            0,
        )
    structured = Path(args.file).read_text(encoding="utf-8")
    paras = dict_mod.accept_structuring(root, args.unit, structured)
    data: dict[str, Any] = {"paragraphs": paras}
    if args.raw_file:
        raw = Path(args.raw_file).read_text(encoding="utf-8")
        data["preserved_phrase_share"] = dict_mod.preserved_phrase_share(raw, structured)
    return (
        build_envelope(
            command="dictation",
            status="ok",
            lang=lang,
            message_key="draft.dictation_accepted",
            message_params={"unit": args.unit},
            data=data,
        ),
        0,
    )


def _provenance(args: Any, root: Path, lang: str) -> tuple[dict[str, Any], int]:
    if args.provenance_action == "show":
        data = (
            {"unit": args.unit, "shares": prov_mod.shares(root, args.unit)}
            if args.unit
            else {"object": prov_mod.object_shares(root)}
        )
        return (
            build_envelope(
                command="provenance",
                status="ok",
                lang=lang,
                message_key="draft.provenance",
                data=data,
            ),
            0,
        )
    from research_harness.gates import interactive

    entry = prov_mod.mark(
        root, args.unit, args.paragraph, args.origin, human_channel=interactive.is_human_channel()
    )
    return (
        build_envelope(
            command="provenance",
            status="ok",
            lang=lang,
            message_key="draft.marked",
            message_params={"paragraph": args.paragraph},
            data={"paragraph": entry},
        ),
        0,
    )
