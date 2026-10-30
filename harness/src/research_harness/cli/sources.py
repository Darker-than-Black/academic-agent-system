"""`rh source import|lookup|link|fulltext|fetch-oa|retraction-check|list` (M2-01)."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from research_harness.cli.context import object_root
from research_harness.core.envelope import build_envelope
from research_harness.core.errors import InvalidInputError
from research_harness.sources import enrich, import_files, registry, retractions

_COMMAND = "source"


def register(sub: argparse._SubParsersAction) -> None:
    sc = sub.add_parser(_COMMAND, help="Sources: import, lookup, link, full text, OA, retractions.")
    sa = sc.add_subparsers(dest="source_action", metavar="action", required=True)

    imp = sa.add_parser("import", help="Import sources from a file, export or DOI list.")
    g = imp.add_mutually_exclusive_group(required=True)
    g.add_argument("--file")
    g.add_argument(
        "--from",
        dest="from_source",
        choices=["scopus", "wos", "scholar", "zotero", "ris", "bibtex", "csv"],
    )
    g.add_argument("--doi", action="append")
    imp.add_argument("export", nargs="?", help="Export file path (with --from).")
    imp.add_argument("--kind", default="file")

    lk = sa.add_parser("lookup", help="Enrich sources and resolve metadata_status.")
    lk.add_argument("ids", nargs="+")
    lk.add_argument("--adapter", action="append")

    ln = sa.add_parser("link", help="Link two sources with a typed relation.")
    ln.add_argument("src")
    ln.add_argument("dst")
    ln.add_argument(
        "--relation", required=True, choices=["duplicate_of", "preprint_of", "published_version_of"]
    )

    ft = sa.add_parser("fulltext", help="Register an author-provided legal full text.")
    ft.add_argument("id")
    ft.add_argument("--file", required=True)
    ft.add_argument(
        "--version", default="unknown", choices=["published", "accepted", "preprint", "unknown"]
    )
    ft.add_argument("--obtained-via", dest="obtained_via", default="author")

    oa = sa.add_parser("fetch-oa", help="Resolve/fetch legal OA full text.")
    oa.add_argument("ids", nargs="+")

    rc = sa.add_parser("retraction-check", help="Check retraction notices (Crossref metadata).")
    rc.add_argument("ids", nargs="+")

    sa.add_parser("list", help="List registered sources.")


def handles(command: str) -> bool:
    return command == _COMMAND


def _env(
    command: str,
    lang: str,
    key: str,
    *,
    status: str = "ok",
    params: dict[str, Any] | None = None,
    findings: list[dict[str, Any]] | None = None,
    data: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], int]:
    return (
        build_envelope(
            command=command,
            status=status,
            lang=lang,
            message_key=key,
            message_params=params,
            findings=findings,
            data=data or {},
        ),
        3 if status == "blocked" else 0,
    )


def route(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = object_root(args)
    action = args.source_action
    if action == "import":
        return _import(args, root, lang)
    if action == "lookup":
        updated, findings = enrich.lookup(
            root,
            args.ids,
            transport=None,
            adapters=tuple(args.adapter) if args.adapter else enrich._DEFAULT_ENRICH,
        )
        return _env(
            _COMMAND,
            lang,
            "source.looked_up",
            params={"n": len(updated)},
            status="partial" if findings else "ok",
            findings=findings,
            data={"sources": updated},
        )
    if action == "link":
        rec = registry.link(root, args.src, args.dst, args.relation)
        return _env(
            _COMMAND,
            lang,
            "source.linked",
            params={"src": args.src, "dst": args.dst},
            data={"source": rec},
        )
    if action == "fulltext":
        rec = import_files.add_fulltext(
            root, args.id, Path(args.file), version=args.version, obtained_via=args.obtained_via
        )
        return _env(
            _COMMAND, lang, "source.fulltext_added", params={"id": args.id}, data={"source": rec}
        )
    if action == "fetch-oa":
        updated, findings = enrich.fetch_oa(root, args.ids, transport=None)
        return _env(
            _COMMAND,
            lang,
            "source.oa_fetched",
            params={"n": len(updated)},
            status="partial" if findings else "ok",
            findings=findings,
            data={"sources": updated},
        )
    if action == "retraction-check":
        return _retraction(args, root, lang)
    if action == "list":
        recs = sorted(registry.load(root), key=registry.sort_key)
        return _env(
            _COMMAND, lang, "source.listed", params={"n": len(recs)}, data={"sources": recs}
        )
    raise InvalidInputError("error.invalid")


def _import(args: Any, root: Path, lang: str) -> tuple[dict[str, Any], int]:
    if args.doi:
        added, findings = import_files.import_doi_list(root, args.doi)
    elif args.from_source:
        if not args.export:
            raise InvalidInputError("error.invalid")
        added, findings = import_files.import_export(root, Path(args.export), args.from_source)
    else:
        src = Path(args.file)
        suffix = src.suffix.lower()
        if suffix in (".bib", ".bibtex"):
            added, findings = import_files.import_export(root, src, "bibtex")
        elif suffix == ".ris":
            added, findings = import_files.import_export(root, src, "ris")
        else:
            added, findings = import_files.import_file(root, src, kind=args.kind)
    return _env(
        _COMMAND,
        lang,
        "source.imported",
        params={"n": len(added)},
        status="partial" if findings else "ok",
        findings=findings,
        data={"sources": added},
    )


def _retraction(args: Any, root: Path, lang: str) -> tuple[dict[str, Any], int]:
    findings: list[dict[str, Any]] = []
    updated: list[dict[str, Any]] = []
    for sid in args.ids:
        source = registry.get(root, sid)
        if source is None:
            raise InvalidInputError("error.invalid")
        doi = source.get("doi")
        if not doi:
            continue
        rec = retractions.check_doi(doi, transport=None)
        source["retraction"] = rec
        registry.update(root, sid, source)
        updated.append(source)
        if rec["status"] == "notice_found":
            findings.append(
                {
                    "check_id": "source.retraction_notice",
                    "severity": "blocker",
                    "reason": f"retraction notice for {sid} ({doi})",
                    "location": {"ref": f"source:{sid}"},
                    "proposed_action": "",
                }
            )
    return _env(
        _COMMAND,
        lang,
        "source.retraction_checked",
        params={"n": len(updated)},
        status="partial" if findings else "ok",
        findings=findings,
        data={"sources": updated},
    )
