"""Glossary (``glossary.json`` + rendered ``manuscript/glossary.md``) and
full-document term checks (undefined term, alias conflict) — cheap, deterministic.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from research_harness.structure import ops
from research_harness.summaries.deterministic import body_of

_TERM_REF = re.compile(r"\{\{term:([^}]+)\}\}")


def glossary_path(root: Path) -> Path:
    return root / "glossary.json"


def rendered_path(root: Path) -> Path:
    return root / "manuscript" / "glossary.md"


def load(root: Path) -> list[dict[str, Any]]:
    path = glossary_path(root)
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("terms", [])


def add_term(
    root: Path,
    *,
    term: str,
    definition: str,
    source: str,
    aliases: list[str] | None = None,
    first_unit: str | None = None,
    language: str = "uk",
) -> dict[str, Any]:
    terms = load(root)
    entry = {
        "term": term,
        "definition": definition,
        "source": source,
        "aliases": aliases or [],
        "first_unit": first_unit,
        "language": language,
    }
    terms = [t for t in terms if t["term"] != term] + [entry]
    glossary_path(root).parent.mkdir(parents=True, exist_ok=True)
    glossary_path(root).write_text(
        json.dumps({"schema_version": "0.2", "terms": terms}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _render(root, terms)
    return entry


def _render(root: Path, terms: list[dict[str, Any]]) -> None:
    lines = ["# Glossary", ""]
    for t in sorted(terms, key=lambda x: x["term"].lower()):
        aliases = f" ({', '.join(t['aliases'])})" if t.get("aliases") else ""
        lines.append(f"- **{t['term']}**{aliases}: {t['definition']}")
    rendered_path(root).parent.mkdir(parents=True, exist_ok=True)
    rendered_path(root).write_text("\n".join(lines) + "\n", encoding="utf-8")


def check(root: Path) -> list[dict[str, Any]]:
    terms = load(root)
    findings: list[dict[str, Any]] = []

    # Alias conflict: one alias (or term) mapped to two different terms.
    owner: dict[str, str] = {}
    for t in terms:
        for name in [t["term"], *t.get("aliases", [])]:
            key = name.lower()
            if key in owner and owner[key] != t["term"]:
                findings.append(
                    {
                        "check_id": "glossary.alias_conflict",
                        "severity": "major",
                        "reason": f"alias {name!r} maps to both {owner[key]!r} and {t['term']!r}",
                        "location": {},
                        "proposed_action": "",
                    }
                )
            else:
                owner[key] = t["term"]

    # Undefined term: a {{term:X}} reference in text that is not in the glossary.
    defined = {t["term"].lower() for t in terms} | {
        a.lower() for t in terms for a in t.get("aliases", [])
    }
    for folder in ops.current_folders(root).values():
        body = body_of((folder / "text.md").read_text(encoding="utf-8"))
        for ref in _TERM_REF.findall(body):
            if ref.strip().lower() not in defined:
                findings.append(
                    {
                        "check_id": "glossary.term_undefined",
                        "severity": "minor",
                        "reason": f"term {ref!r} is used but not defined in the glossary",
                        "location": {},
                        "proposed_action": "",
                    }
                )
    return findings
