"""`rh overlap [--unit U]` — overlap with the author corpus (M3-10, FR-30)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from research_harness.cli.context import object_root
from research_harness.core.envelope import build_envelope
from research_harness.integrity import overlap as overlap_mod
from research_harness.workspace import author as author_mod
from research_harness.workspace.workspace import Workspace

_COMMAND = "overlap"


def register(sub: argparse._SubParsersAction) -> None:
    ov = sub.add_parser(_COMMAND, help="Overlap of the current text with the author corpus.")
    ov.add_argument("--unit", help="Limit to one unit id.")
    ov.add_argument("--against", default="corpus", choices=["corpus"], help="Overlap target.")


def handles(command: str) -> bool:
    return command == _COMMAND


def route(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = object_root(args)
    corpus_dir: Path | None = None
    try:
        ws = Workspace.find(getattr(args, "workspace", None))
        corpus_dir = author_mod.author_dir(ws) / "corpus"
    except Exception:
        corpus_dir = None

    report = overlap_mod.run(root, unit=args.unit, corpus_dir=corpus_dir)
    findings = overlap_mod.findings_from(report)
    _write_report(root, report)

    status = "ok" if report["result"] == "ok" else "partial"
    return (
        build_envelope(
            command=_COMMAND,
            status=status,
            lang=lang,
            message_key="overlap.done",
            message_params={"n": len(report["matches"]), "result": report["result"]},
            findings=findings,
            data={"report": report},
        ),
        0,
    )


def _write_report(root: Path, report: dict[str, Any]) -> None:
    d = root / "integrity" / "overlap"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{report['run_id']}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
