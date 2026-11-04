"""Review methodology record: search log, selection criteria, included studies.

For a ``review`` article the corpus must be reproducible: which sources were
searched, with what queries and dates, how many were found/screened/included/
excluded and why, the inclusion/exclusion criteria, and every included study
identified (not only the fulltext ones). This module stores that record, checks
it for the deficits readiness cares about, and renders an included-studies table
for the methods section. It never invents a number or a source (H6); a missing
value stays ``unknown`` (H7, represented as ``null`` / absence).

Not in this slice: auto-injecting the rendered table into the methods unit on
export (no reliable ``methods`` unit marker yet — a structure follow-up), the
PRISMA flow figure (M4-14), and binding the deficits into the G1 readiness gate
(M4-15 gate is deferred); ``deficits()`` is ready for that gate to call.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_harness.schemas import validate
from research_harness.sources import registry

_UNIDENTIFIED_STATUS = ("unresolved", "not_found")


def path(root: Path) -> Path:
    return root / "methodology" / "review.json"


def load(root: Path) -> dict[str, Any] | None:
    p = path(root)
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def save(root: Path, data: dict[str, Any]) -> dict[str, Any]:
    data.setdefault("schema_version", "0.2")
    errors = validate("review-methodology", data)
    if errors:
        raise ValueError(f"invalid review methodology: {errors}")
    p = path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return data


def _f(check_id: str, reason: str, *, ref: str | None = None, action: str = "") -> dict[str, Any]:
    location: dict[str, Any] = {}
    if ref is not None:
        location["ref"] = ref
    return {
        "check_id": check_id,
        "severity": "major",
        "reason": reason,
        "location": location,
        "proposed_action": action,
    }


def _has_search_log(data: dict[str, Any]) -> bool:
    sl = data.get("search_log") or {}
    return bool(sl.get("databases")) or bool(sl.get("counts"))


def _has_criteria(data: dict[str, Any]) -> bool:
    sc = data.get("selection_criteria") or {}
    return bool(sc.get("inclusion"))


def _unidentified(source: dict[str, Any]) -> bool:
    return (
        source.get("metadata_status") in _UNIDENTIFIED_STATUS
        or not source.get("title")
        or not source.get("authors")
    )


def deficits(root: Path) -> list[dict[str, Any]]:
    """Readiness deficits for a reproducible review corpus (major findings)."""
    data = load(root) or {}
    findings: list[dict[str, Any]] = []
    if not _has_search_log(data):
        findings.append(
            _f(
                "methodology.search_log_missing",
                "no search log: databases/queries/dates/counts are not recorded",
                action="Record the search with `rh methodology set` (unknown counts stay unknown).",
            )
        )
    if not _has_criteria(data):
        findings.append(
            _f(
                "methodology.selection_criteria_missing",
                "no selection criteria: inclusion/exclusion rules are not stated",
                action="State inclusion/exclusion criteria with `rh methodology set`.",
            )
        )
    for source in registry.load(root):
        if _unidentified(source):
            sid = source.get("id", "?")
            findings.append(
                _f(
                    "methodology.corpus_unidentified",
                    f"corpus source {sid} is not fully identified (status/title/authors missing)",
                    ref=f"source:{sid}",
                    action="Resolve the source metadata so every corpus study is identified.",
                )
            )
    return findings


def _citation(source: dict[str, Any]) -> str:
    authors = "; ".join(
        f"{a.get('family', '')} {a.get('given', '')}".strip() for a in source.get("authors", [])
    )
    year = source.get("year")
    title = source.get("title") or "—"
    bits = [b for b in (authors, f"({year})" if year else "", title) if b]
    return " ".join(bits)


def methods_markdown(root: Path, cite_numbers: dict[str, int] | None = None) -> str:
    """Render selection criteria, the search summary and the included-studies table.

    When ``cite_numbers`` (bib_key -> citation number) is given, the included-
    sources table is ordered by that number and its № column shows it, so the
    table lines up with the in-text citations and the reference list instead of a
    standalone row index. Uncited sources sort last and show "—".
    """
    data = load(root) or {}
    # Each entry in ``blocks`` is one Markdown block (heading, paragraph, list or
    # table); they are joined by a blank line so pandoc parses each as its own
    # block. Multi-line blocks (the list, the table) keep single newlines inside.
    blocks: list[str] = []

    sc = data.get("selection_criteria") or {}
    if sc.get("inclusion") or sc.get("exclusion"):
        blocks.append("## Критерії відбору")
        if sc.get("inclusion"):
            blocks.append("**Включення:** " + "; ".join(sc["inclusion"]))
        if sc.get("exclusion"):
            blocks.append("**Виключення:** " + "; ".join(sc["exclusion"]))

    sl = data.get("search_log") or {}
    if sl.get("databases") or sl.get("counts"):
        blocks.append("## Стратегія пошуку")
        items: list[str] = []
        for db in sl.get("databases", []):
            found = db.get("found")
            found_s = "невідомо" if found is None else str(found)
            q = f": «{db['query']}»" if db.get("query") else ""
            date = f", {db['date']}" if db.get("date") else ""
            items.append(f"- {db['name']}{q}{date}; знайдено: {found_s}")
        counts = sl.get("counts") or {}
        if counts:

            def c(k: str) -> str:
                v = counts.get(k)
                return "невідомо" if v is None else str(v)

            items.append(
                f"- Усього: знайдено {c('found')}, відсіяно {c('screened')}, "
                f"включено {c('included')}, виключено {c('excluded')}"
            )
        if items:
            blocks.append("\n".join(items))

    sources = registry.load(root)
    if sources:
        roles = {i["source_id"]: i.get("role", "") for i in data.get("included", [])}
        if cite_numbers:
            # Order by citation number; uncited sources (no number) keep registry
            # order after the cited ones.
            sources = sorted(sources, key=lambda s: cite_numbers.get(s.get("bib_key"), 10**6))
        blocks.append("## Включені джерела")
        table = ["| № | Джерело | Доступ | Роль |", "|---|---------|--------|------|"]
        for i, s in enumerate(sources, start=1):
            sid = s.get("id", "?")
            access = s.get("access_level", "unknown")
            num = (cite_numbers or {}).get(s.get("bib_key"))
            label = str(num) if num is not None else (str(i) if cite_numbers is None else "—")
            table.append(f"| {label} | {_citation(s)} | {access} | {roles.get(sid, '')} |")
        blocks.append("\n".join(table))

    return "\n\n".join(blocks)
