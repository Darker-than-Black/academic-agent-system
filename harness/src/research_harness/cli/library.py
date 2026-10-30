"""`rh library index|search|page` and `rh quote check` (M2-02)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from research_harness.cli.context import object_root
from research_harness.core.envelope import build_envelope
from research_harness.core.errors import InvalidInputError
from research_harness.library import index as index_mod
from research_harness.library import ingest, quotes
from research_harness.sources import registry

_LIBRARY = "library"
_QUOTE = "quote"


def register(sub: argparse._SubParsersAction) -> None:
    lb = sub.add_parser(_LIBRARY, help="Local full-text library: index, search, page.")
    la = lb.add_subparsers(dest="library_action", metavar="action", required=True)
    la.add_parser("index", help="Extract full texts and (re)build the FTS index.")
    se = la.add_parser("search", help="Full-text search across the library.")
    se.add_argument("query")
    se.add_argument("--limit", type=int, default=20)
    pg = la.add_parser("page", help="Show one page's stored text.")
    pg.add_argument("source")
    pg.add_argument("--page", type=int, required=True)
    pg.add_argument("--printed", action="store_true", help="--page is a printed page number.")

    qt = sub.add_parser(_QUOTE, help="Deterministic quote/excerpt check.")
    qa = qt.add_subparsers(dest="quote_action", metavar="action", required=True)
    ck = qa.add_parser("check", help="Check excerpts (JSON file) or a unit's excerpts.")
    g = ck.add_mutually_exclusive_group(required=True)
    g.add_argument("--file", help="JSON list of excerpts: [{source_id, text, locator}].")
    g.add_argument("--unit", help="Unit id (reads the unit's excerpts; M2-04).")


def handles(command: str) -> bool:
    return command in (_LIBRARY, _QUOTE)


def route(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = object_root(args)
    if args.command == _LIBRARY:
        return _library(args, root, lang)
    return _quote(args, root, lang)


def _library(args: Any, root: Path, lang: str) -> tuple[dict[str, Any], int]:
    action = args.library_action
    if action == "index":
        n, findings = ingest.ingest_all(root)
        return (
            build_envelope(
                command=_LIBRARY,
                status="partial" if findings else "ok",
                lang=lang,
                message_key="library.indexed",
                message_params={"n": n},
                findings=findings,
                data={"sources": n},
            ),
            0,
        )
    if action == "search":
        rows = index_mod.search(root, args.query, limit=args.limit)
        return (
            build_envelope(
                command=_LIBRARY,
                status="ok",
                lang=lang,
                message_key="library.searched",
                message_params={"n": len(rows)},
                data={"results": rows},
            ),
            0,
        )
    if action == "page":
        pdf_page = args.page
        if args.printed:
            source = registry.get(root, args.source)
            pmap = (source or {}).get("page_map") or {}
            from research_harness.library.pagemap import pdf_for_printed

            mapped = pdf_for_printed(pmap, str(args.page))
            if mapped is None:
                raise InvalidInputError("error.invalid")
            pdf_page = mapped
        text = index_mod.page(root, args.source, pdf_page)
        return (
            build_envelope(
                command=_LIBRARY,
                status="ok" if text is not None else "partial",
                lang=lang,
                message_key="library.page",
                message_params={"source": args.source, "page": pdf_page},
                data={
                    "source_id": args.source,
                    "pdf_page": pdf_page,
                    "text": text,
                    "_text": text or "",
                },
            ),
            0,
        )
    raise InvalidInputError("error.invalid")


def _quote(args: Any, root: Path, lang: str) -> tuple[dict[str, Any], int]:
    if args.quote_action != "check":
        raise InvalidInputError("error.invalid")
    if args.unit:
        # Unit excerpts arrive with the synthesis desk (M2-04); none to check yet.
        excerpts: list[dict[str, Any]] = []
    else:
        excerpts = json.loads(Path(args.file).read_text(encoding="utf-8"))
    page_maps = {s["id"]: s.get("page_map", {}) for s in registry.load(root)}
    results, findings = quotes.check_excerpts(root, excerpts, page_maps=page_maps)
    passed = sum(1 for r in results if r["result"] == "pass")
    return (
        build_envelope(
            command=_QUOTE,
            status="partial" if findings else "ok",
            lang=lang,
            message_key="quote.checked",
            message_params={"passed": passed, "total": len(results)},
            findings=findings,
            data={"results": results},
        ),
        0,
    )
