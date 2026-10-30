"""References: collect cited keys, build a BibTeX file from the registry, sort
per the style (Cyrillic-aware, transliteration-insensitive), and flag any cited
key that does not resolve to a non-``not_found`` registry record (T43, H6).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from research_harness.sources import registry
from research_harness.structure import ops
from research_harness.summaries.deterministic import body_of

_CITE = re.compile(r"@([A-Za-z0-9:_-]+)|\[\[cite:([^\]]+)\]\]")


def cited_keys(root: Path) -> set[str]:
    keys: set[str] = set()
    for _uid, folder in ops.current_folders(root).items():
        tf = folder / "text.md"
        if tf.is_file():
            body = body_of(tf.read_text(encoding="utf-8"))
            for m in _CITE.finditer(body):
                keys.add(m.group(1) or m.group(2))
    return keys


def _by_bib_key(root: Path) -> dict[str, dict[str, Any]]:
    return {r["bib_key"]: r for r in registry.load(root) if r.get("bib_key")}


def build(root: Path) -> tuple[str, list[dict[str, Any]]]:
    """Return (references.bib text, gaps). A cited key that resolves to nothing
    or to a ``not_found`` record is a gap and is excluded (never fabricated).
    """
    index = _by_bib_key(root)
    gaps: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    for key in sorted(cited_keys(root)):
        rec = index.get(key)
        if rec is None or rec.get("metadata_status") == "not_found":
            gaps.append(
                {
                    "check_id": "export.cite_unresolved",
                    "severity": "blocker",
                    "reason": f"cited key {key!r} resolves to no usable registry record",
                    "location": {},
                    "proposed_action": "",
                }
            )
            continue
        records.append(rec)

    records.sort(key=registry.sort_key)
    return _bibtex(records), gaps


def _bibtex(records: list[dict[str, Any]]) -> str:
    out: list[str] = []
    for r in records:
        authors = " and ".join(
            f"{a.get('family', '')}, {a.get('given', '')}".strip(", ") for a in r.get("authors", [])
        )
        fields = {
            "author": authors,
            "title": r.get("title", ""),
            "year": r.get("year", ""),
            "journal": r.get("container", ""),
            "doi": r.get("doi", ""),
        }
        body = ",\n  ".join(f"{k} = {{{v}}}" for k, v in fields.items() if v)
        out.append(f"@article{{{r['bib_key']},\n  {body}\n}}")
    return "\n\n".join(out) + ("\n" if out else "")
