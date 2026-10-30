"""Paragraph map (``<unit>/provenance.json``): id, text hash and origin per
paragraph, plus origin shares for status (FR-53).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_harness.core.errors import BlockedError
from research_harness.schemas import validate
from research_harness.structure import ops
from research_harness.units.anchors import paragraph_sha

ORIGINS = ("author", "agent", "agent_edited_by_author")
# Marking toward less AI involvement changes what the AI-use statement says
# (FR-32), so it follows the human-channel rule (02 §9.3).
_LESS_AI = {
    ("agent", "agent_edited_by_author"),
    ("agent", "author"),
    ("agent_edited_by_author", "author"),
}


def provenance_path(root: Path, unit_id: str) -> Path:
    return ops.current_folders(root)[unit_id] / "provenance.json"


def load_map(root: Path, unit_id: str) -> dict[str, dict[str, Any]]:
    path = provenance_path(root, unit_id)
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {p["id"]: p for p in data.get("paragraphs", [])}


def save_map(root: Path, unit_id: str, paragraphs: list[dict[str, Any]]) -> None:
    doc = {"schema_version": "0.2", "unit_id": unit_id, "paragraphs": paragraphs}
    errors = validate("paragraph-map", doc)
    if errors:
        raise ValueError(f"invalid paragraph map: {errors}")
    provenance_path(root, unit_id).write_text(
        json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def apply_write(
    root: Path, unit_id: str, paras: list[dict[str, str]], *, by: str
) -> list[dict[str, Any]]:
    """Update the map after a write. ``by`` is 'agent' or 'author'.

    A new or changed paragraph gets origin ``by``; when the author edits a
    paragraph previously written by the agent, its origin becomes
    ``agent_edited_by_author`` (FR-53).
    """
    prev = load_map(root, unit_id)
    out: list[dict[str, Any]] = []
    for p in paras:
        pid, text = p["id"], p["text"]
        sha = paragraph_sha(text)
        old = prev.get(pid)
        if old and old["sha256"] == sha:
            out.append(old)  # unchanged
            continue
        if by == "author" and old and old["origin"] == "agent":
            origin = "agent_edited_by_author"
        else:
            origin = by
        history = (old or {}).get("history", [])
        if old:
            history = [*history, {"sha256": old["sha256"], "origin": old["origin"]}]
        out.append({"id": pid, "sha256": sha, "origin": origin, "history": history})
    save_map(root, unit_id, out)
    return out


def mark(root: Path, unit_id: str, paragraph_id: str, origin: str, *, human_channel: bool = False):
    """Set a paragraph's origin. Moving toward less AI needs the human channel."""
    pmap = load_map(root, unit_id)
    entry = pmap.get(paragraph_id)
    if entry is None:
        raise ValueError(f"unknown paragraph {paragraph_id}")
    if (entry["origin"], origin) in _LESS_AI and not human_channel:
        raise BlockedError("error.provenance_human_only")
    entry["origin"] = origin
    save_map(root, unit_id, list(pmap.values()))
    return entry


def shares(root: Path, unit_id: str) -> dict[str, int]:
    counts = {o: 0 for o in ORIGINS}
    for entry in load_map(root, unit_id).values():
        counts[entry["origin"]] = counts.get(entry["origin"], 0) + 1
    return counts


def object_shares(root: Path) -> dict[str, int]:
    counts = {o: 0 for o in ORIGINS}
    for uid in ops.current_folders(root):
        for o, n in shares(root, uid).items():
            counts[o] += n
    return counts
