"""Folder-name computation for units (02 §7.1)."""

from __future__ import annotations

from research_harness.core.paths import sanitize_name
from research_harness.structure.model import Unit


def compute_paths(units: list[Unit], labels: dict[str, str]) -> dict[str, str]:
    """Return unit id -> manuscript-relative folder path, per 02 §7.1."""
    paths: dict[str, str] = {}
    chapter_k = 0
    for pos, u in enumerate(units, start=1):
        if u.kind == "chapter":
            chapter_k += 1
            top = f"{pos:02d} {labels['chapter']} {chapter_k}. {u.title or ''}"
        else:
            top = f"{pos:02d} {u.title or ''}"
        top = sanitize_name(top)
        paths[u.id] = f"manuscript/{top}"
        _child_paths(u, chapter_k, labels, paths, parent=f"manuscript/{top}")
    return paths


def _child_paths(
    chapter: Unit, k: int, labels: dict[str, str], paths: dict[str, str], parent: str
) -> None:
    subsection_m = 0
    # chapter_conclusions is numbered after the last subsection.
    n_subsections = sum(1 for c in chapter.children if c.kind == "subsection")
    for c in chapter.children:
        if c.kind == "chapter_conclusions":
            m = n_subsections + 1
            name = f"{k}.{m} {labels['chapter_conclusions']} {k}"
        else:
            subsection_m += 1
            name = f"{k}.{subsection_m} {c.title or ''}"
        name = sanitize_name(name)
        paths[c.id] = f"{parent}/{name}"
