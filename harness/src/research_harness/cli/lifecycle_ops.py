"""`rh lock|unlock|record|reviews|revise` (M3-08, lifecycle-records.md).

`unlock` and `record` are human-only (they change frozen state / describe
external facts): in an agent channel they write nothing and return a request
with ``who: author`` (exit 3, ASR-04/H14).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from research_harness.cli.context import object_root
from research_harness.core.envelope import build_envelope
from research_harness.gates.interactive import is_human_channel
from research_harness.intake.answers import answers_path
from research_harness.intake.answers import load as load_answers
from research_harness.lifecycle import locks as locks_mod
from research_harness.lifecycle import records as records_mod
from research_harness.lifecycle import reviews as reviews_mod
from research_harness.state.snapshot import atomic_write_bytes

_COMMANDS = {"lock", "unlock", "record", "reviews", "revise"}


def register(sub: argparse._SubParsersAction) -> None:
    lk = sub.add_parser("lock", help="Lock a unit (no further writes until unlocked).")
    lk.add_argument("unit")
    lk.add_argument("--reason", required=True)

    ul = sub.add_parser("unlock", help="Unlock a unit (human terminal only).")
    ul.add_argument("unit")

    rc = sub.add_parser("record", help="Record a submission or publication (human only).")
    rsa = rc.add_subparsers(dest="record_kind", metavar="kind", required=True)
    sub_s = rsa.add_parser("submission")
    sub_s.add_argument("--venue", required=True)
    sub_s.add_argument("--issn", action="append", default=None)
    sub_s.add_argument("--date", required=True)
    sub_s.add_argument("--manuscript-id", dest="manuscript_id", default=None)
    sub_s.add_argument("--channel-note", dest="channel_note", default="")
    sub_p = rsa.add_parser("publication")
    sub_p.add_argument("--submission", required=True)
    sub_p.add_argument("--date", required=True)
    for opt in ("doi", "volume", "issue", "pages", "license", "url"):
        sub_p.add_argument(f"--{opt}", default=None)

    rv = sub.add_parser("reviews", help="Reviewer comments (respond_to_reviewers, A14).")
    rva = rv.add_subparsers(dest="reviews_action", metavar="action", required=True)
    add = rva.add_parser("add")
    add.add_argument("file", help="File whose text is the reviewer comment.")
    add.add_argument("--round", type=int, required=True)
    add.add_argument("--reviewer", required=True)
    add.add_argument("--location-hint", dest="location_hint", default=None)
    rva.add_parser("table")
    resp = rva.add_parser("respond")
    resp.add_argument("--comment", required=True)
    resp.add_argument("--action", required=True, choices=["accept", "partial", "decline"])
    resp.add_argument("--response", required=True)
    resp.add_argument("--changed-units", dest="changed_units", default=None)
    resp.add_argument("--evidence-refs", dest="evidence_refs", default=None)

    re = sub.add_parser("revise", help="Enter revise mode with an agreed scope.")
    re.add_argument(
        "--from", dest="from_file", default=None, help="Original FILE.md (.docx = M3-09)."
    )
    re.add_argument("--scope", action="append", default=None, help="Unit id in scope (repeatable).")


def handles(command: str) -> bool:
    return command in _COMMANDS


def _human_only(command: str, lang: str) -> tuple[dict[str, Any], int]:
    return (
        build_envelope(
            command=command,
            status="blocked",
            lang=lang,
            message_key="error.record_human_only",
            next_actions=[{"who": "author", "action": f"rh {command} … (own terminal)"}],
        ),
        3,
    )


def route(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = object_root(args)
    cmd = args.command
    if cmd == "lock":
        rec = locks_mod.lock(root, args.unit, reason=args.reason, locked_by="author")
        return _ok("lock", lang, "lock.locked", {"unit": args.unit}, {"lock": rec})
    if cmd == "unlock":
        if not is_human_channel():
            return _human_only("unlock", lang)
        existed = locks_mod.unlock(root, args.unit)
        return _ok("unlock", lang, "lock.unlocked", {"unit": args.unit}, {"was_locked": existed})
    if cmd == "record":
        return _record(root, args, lang)
    if cmd == "reviews":
        return _reviews(root, args, lang)
    return _revise(root, args, lang)


def _record(root: Path, args: Any, lang: str) -> tuple[dict[str, Any], int]:
    if not is_human_channel():
        return _human_only("record", lang)
    if args.record_kind == "submission":
        rec = records_mod.record_submission(
            root,
            venue_title=args.venue,
            date=args.date,
            channel_note=args.channel_note,
            issn=args.issn,
            manuscript_id=args.manuscript_id,
        )
    else:
        rec = records_mod.record_publication(
            root,
            submission_id=args.submission,
            date=args.date,
            doi=args.doi,
            volume=args.volume,
            issue=args.issue,
            pages=args.pages,
            license=args.license,
            url=args.url,
        )
    return _ok("record", lang, "record.done", {"id": rec["id"]}, {"record": rec})


def _reviews(root: Path, args: Any, lang: str) -> tuple[dict[str, Any], int]:
    if args.reviews_action == "add":
        text = (
            (root / args.file).read_text(encoding="utf-8")
            if (root / args.file).is_file()
            else Path(args.file).read_text(encoding="utf-8")
        )
        rec = reviews_mod.add_comment(
            root,
            round=args.round,
            reviewer=args.reviewer,
            text=text.strip(),
            location_hint=args.location_hint,
        )
        return _ok("reviews", lang, "reviews.added", {"id": rec["id"]}, {"comment": rec})
    if args.reviews_action == "table":
        items = reviews_mod.list_comments(root)
        return _ok(
            "reviews",
            lang,
            "reviews.table",
            {"n": len(items), "open": reviews_mod.open_count(root)},
            {"comments": items},
        )
    units = [u.strip() for u in args.changed_units.split(",")] if args.changed_units else None
    refs = [r.strip() for r in args.evidence_refs.split(",")] if args.evidence_refs else None
    rec = reviews_mod.respond(
        root,
        args.comment,
        action=args.action,
        response=args.response,
        changed_units=units,
        evidence_refs=refs,
    )
    return _ok("reviews", lang, "reviews.responded", {"id": rec["id"]}, {"comment": rec})


def _revise(root: Path, args: Any, lang: str) -> tuple[dict[str, Any], int]:
    if args.from_file and args.from_file.lower().endswith(".docx"):
        return (
            build_envelope(
                command="revise", status="blocked", lang=lang, message_key="error.docx_import_m3_09"
            ),
            3,
        )
    data = load_answers(root)
    data["mode"] = "revise"
    atomic_write_bytes(
        answers_path(root), (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )
    scope = args.scope or []
    revise_dir = root / "revise"
    revise_dir.mkdir(parents=True, exist_ok=True)
    (revise_dir / "scope.json").write_text(
        json.dumps({"scope": scope}, ensure_ascii=False), encoding="utf-8"
    )
    if args.from_file:
        src = root / args.from_file if (root / args.from_file).is_file() else Path(args.from_file)
        (revise_dir / "original.md").write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    # Units outside scope are proposed for locking — the author confirms (rh lock).
    next_actions = [
        {
            "who": "author",
            "action": "Confirm locks for units outside the revise scope (rh lock U --reason …).",
        }
    ]
    return (
        build_envelope(
            command="revise",
            status="ok",
            lang=lang,
            message_key="revise.entered",
            message_params={"n": len(scope)},
            data={"scope": scope},
            next_actions=next_actions,
        ),
        0,
    )


def _ok(
    command: str, lang: str, key: str, params: dict[str, Any], data: dict[str, Any]
) -> tuple[dict[str, Any], int]:
    return (
        build_envelope(
            command=command,
            status="ok",
            lang=lang,
            message_key=key,
            message_params=params,
            data=data,
        ),
        0,
    )
