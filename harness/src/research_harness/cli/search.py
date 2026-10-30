"""`rh search plan|run|log|stop|coverage`, `rh screen`, `rh lab journal add` (M2-03)."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

from research_harness.cli.context import object_root
from research_harness.core.envelope import build_envelope
from research_harness.core.errors import InvalidInputError
from research_harness.lab import journal as journal_mod
from research_harness.lab import plan as plan_mod
from research_harness.lab import screening as screening_mod
from research_harness.lab import searchlog


def register(sub: argparse._SubParsersAction) -> None:
    se = sub.add_parser("search", help="Search plan, run, manual log, stop, coverage.")
    sa = se.add_subparsers(dest="search_action", metavar="action", required=True)
    pl = sa.add_parser("plan", help="Validate and store a search plan (versioned).")
    pl.add_argument("--file", required=True)
    rn = sa.add_parser("run", help="Run an API search through an adapter.")
    rn.add_argument("--adapter", required=True)
    rn.add_argument("--query", required=True)
    lg = sa.add_parser("log", help="Record a manual search or export.")
    lg.add_argument("--resource", required=True)
    lg.add_argument("--query", required=True)
    lg.add_argument("--results", type=int, required=True)
    lg.add_argument("--file")
    lg.add_argument(
        "--mode",
        default="manual_export",
        choices=["manual_export", "manual_record", "browser_assisted"],
    )
    st = sa.add_parser("stop", help="Record a search stop with its reason.")
    st.add_argument("--reason", required=True, choices=["saturation", "budget", "author"])
    st.add_argument("--uncovered", help="File listing uncovered resources/areas.")
    sa.add_parser("coverage", help="Show per-resource search coverage.")

    sc = sub.add_parser("screen", help="Include/exclude a candidate with a reason.")
    sc.add_argument("--source", required=True)
    g = sc.add_mutually_exclusive_group(required=True)
    g.add_argument("--include", action="store_true")
    g.add_argument("--exclude", action="store_true")
    sc.add_argument("--reason", default="")

    lb = sub.add_parser("lab", help="Lab journal.")
    la = lb.add_subparsers(dest="lab_action", metavar="action", required=True)
    jn = la.add_parser("journal", help="Lab journal.")
    jna = jn.add_subparsers(dest="journal_action", metavar="action", required=True)
    add = jna.add_parser("add", help="Append a journal entry (append-only).")
    add.add_argument(
        "--kind",
        required=True,
        choices=[
            "question",
            "hypothesis",
            "plan_change",
            "dead_end",
            "deviation",
            "cost",
            "note",
            "decision",
        ],
    )
    add.add_argument("--text", required=True)
    add.add_argument("--model-id", dest="model_id")
    add.add_argument("--cost")


def handles(command: str) -> bool:
    return command in ("search", "screen", "lab")


def route(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = object_root(args)
    if args.command == "search":
        return _search(args, root, lang)
    if args.command == "screen":
        return _screen(args, root, lang)
    return _lab(args, root, lang)


def _env(cmd, lang, key, *, status="ok", params=None, findings=None, data=None):
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
        0,
    )


def _search(args: Any, root: Path, lang: str) -> tuple[dict[str, Any], int]:
    action = args.search_action
    if action == "plan":
        plan = yaml.safe_load(Path(args.file).read_text(encoding="utf-8"))
        stored, findings = plan_mod.save_plan(root, plan)
        blocked = any(f["severity"] == "blocker" for f in findings)
        return _env(
            "search",
            lang,
            "search.plan_saved",
            params={"v": stored.get("version")},
            status="blocked" if blocked else ("partial" if findings else "ok"),
            findings=findings,
            data={"plan": stored},
        )[0], (3 if blocked else 0)
    if action == "run":
        line, added = searchlog.run_search(root, args.adapter, args.query)
        return _env(
            "search",
            lang,
            "search.ran",
            params={"adapter": args.adapter, "n": len(added)},
            data={"log": line, "added": added},
        )
    if action == "log":
        line = searchlog.manual_log(
            root,
            args.resource,
            args.query,
            args.results,
            export_file=Path(args.file) if args.file else None,
            mode=args.mode,
        )
        return _env(
            "search", lang, "search.logged", params={"resource": args.resource}, data={"log": line}
        )
    if action == "stop":
        uncovered = []
        if args.uncovered:
            uncovered = [
                ln.strip()
                for ln in Path(args.uncovered).read_text(encoding="utf-8").splitlines()
                if ln.strip()
            ]
        entry = searchlog.record_stop(root, args.reason, uncovered)
        return _env(
            "search", lang, "search.stopped", params={"reason": args.reason}, data={"stop": entry}
        )
    if action == "coverage":
        cov = searchlog.coverage(root)
        return _env(
            "search", lang, "search.coverage", params={"n": len(cov)}, data={"coverage": cov}
        )
    raise InvalidInputError("error.invalid")


def _screen(args: Any, root: Path, lang: str) -> tuple[dict[str, Any], int]:
    entry, findings = screening_mod.screen(
        root, args.source, include=args.include, reason=args.reason
    )
    return _env(
        "screen",
        lang,
        "screen.recorded",
        params={"source": args.source, "decision": entry["decision"]},
        status="partial" if findings else "ok",
        findings=findings,
        data={"screening": entry},
    )


def _lab(args: Any, root: Path, lang: str) -> tuple[dict[str, Any], int]:
    if args.lab_action != "journal" or args.journal_action != "add":
        raise InvalidInputError("error.invalid")
    entry = journal_mod.add(root, args.kind, args.text, model_id=args.model_id, cost=args.cost)
    return _env("lab", lang, "lab.journal_added", params={"kind": args.kind}, data={"entry": entry})
