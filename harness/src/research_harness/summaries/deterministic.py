"""Deterministic summary part (CLI, no LLM — FR-47). Everything here is computed
from the unit's own text and is reproducible.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from research_harness.core.hashing import text_hash
from research_harness.structure import ops
from research_harness.summaries import SHEET_CHARS

_CITE = re.compile(r"@([A-Za-z0-9:_-]+)|\[\[cite:([^\]]+)\]\]")
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
_PLACEHOLDER = re.compile(r"\[\[AUTHOR:")
_CROSSREF = re.compile(r"\{\{ref:(U-[0-9A-HJKMNP-TV-Z]{8})\}\}")
_FRONT = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)


def summary_path(folder: Path) -> Path:
    return folder / "summary.md"


def body_of(text_md: str) -> str:
    """Return a text.md body without its YAML front matter."""
    m = _FRONT.match(text_md)
    return m.group(2) if m else text_md


def load_summary(folder: Path) -> dict[str, Any]:
    path = summary_path(folder)
    if not path.is_file():
        return {}
    m = _FRONT.match(path.read_text(encoding="utf-8"))
    return (yaml.safe_load(m.group(1)) or {}) if m else {}


def _claims(folder: Path) -> list[str]:
    cf = folder / "claims.json"
    if not cf.is_file():
        return []
    try:
        data = json.loads(cf.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return [c["id"] for c in data.get("claims", []) if isinstance(c, dict) and "id" in c]


def compute(
    body: str, *, known_units: set[str], terms: list[str], claims: list[str]
) -> dict[str, Any]:
    paragraphs = [b for b in re.split(r"\n\s*\n", body.strip()) if b.strip()]
    cite_keys = sorted({m.group(1) or m.group(2) for m in _CITE.finditer(body)})
    numbers = [{"value": n} for n in _NUMBER.findall(body)]
    cross = [{"target_unit": u, "resolved": u in known_units} for u in _CROSSREF.findall(body)]
    terms_used = sorted({t for t in terms if t and t.lower() in body.lower()})
    chars = len(body)
    return {
        "chars_with_spaces": chars,
        "author_sheets": round(chars / SHEET_CHARS, 3),
        "paragraphs": len(paragraphs),
        "cite_keys": cite_keys,
        "numbers": numbers,
        "terms_used": terms_used,
        "cross_refs": cross,
        "placeholders": len(_PLACEHOLDER.findall(body)),
        "claims": claims,
    }


def build_unit(root: Path, unit_id: str, *, terms: list[str] | None = None) -> dict[str, Any]:
    """Compute and store the deterministic summary for a unit; keep any semantic
    part only while the text hash is unchanged.
    """
    folders = ops.current_folders(root)
    folder = folders[unit_id]
    body = body_of((folder / "text.md").read_text(encoding="utf-8"))
    text_sha = text_hash(body.encode("utf-8"))

    known = set(folders)
    deterministic = compute(body, known_units=known, terms=terms or [], claims=_claims(folder))

    prev = load_summary(folder)
    summary: dict[str, Any] = {
        "schema_version": "0.2",
        "target_id": unit_id,
        "level": "unit",
        "text_sha256": text_sha,
        "deterministic": deterministic,
        "stale": False,
    }
    if prev.get("semantic") and prev.get("text_sha256") == text_sha:
        summary["semantic"] = prev["semantic"]  # still valid for this hash
    _write(folder, summary)
    return summary


def _write(folder: Path, summary: dict[str, Any]) -> None:
    from research_harness.schemas import validate

    errors = validate("summary", summary)
    if errors:
        raise ValueError(f"invalid summary: {errors}")
    body = summary.get("semantic", {}).get("main_thesis", "")
    front = yaml.safe_dump(summary, allow_unicode=True, sort_keys=False)
    summary_path(folder).write_text(f"---\n{front}---\n{body}\n", encoding="utf-8")


def current_text_sha(root: Path, unit_id: str) -> str | None:
    folder = ops.current_folders(root).get(unit_id)
    if folder is None or not (folder / "text.md").is_file():
        return None
    return text_hash(body_of((folder / "text.md").read_text(encoding="utf-8")).encode("utf-8"))
