"""Document map (``manuscript/map.md``), chapter summaries and freshness.

Changing a unit's text makes its unit summary, its chapter summary and map.md
stale (FR-47, T51). Integration-level work is refused while anything is stale.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_harness.core.errors import BlockedError
from research_harness.structure import model, ops
from research_harness.summaries.deterministic import build_unit, current_text_sha, load_summary


def map_path(root: Path) -> Path:
    return root / "manuscript" / "map.md"


def _chapter_summary_path(root: Path, chapter_id: str) -> Path:
    return root / "summaries" / f"{chapter_id}.json"


def _tree(root: Path) -> list[model.Unit]:
    folder = root
    data = model.load(folder)
    return model.parse_units(data)


def _leaf_ids(units: list[model.Unit]) -> list[str]:
    out: list[str] = []
    for u in units:
        if u.children:
            out.extend(_leaf_ids(u.children))
        else:
            out.append(u.id)
    return out


def _chapters(units: list[model.Unit]) -> list[model.Unit]:
    return [u for u in units if u.children]


def build(root: Path, *, terms: list[str] | None = None) -> dict[str, Any]:
    """Rebuild unit summaries, chapter summaries and map.md from current text."""
    units = _tree(root)
    folders = ops.current_folders(root)

    for uid in _leaf_ids(units):
        if uid in folders:
            build_unit(root, uid, terms=terms)

    for ch in _chapters(units):
        child_hashes = {
            cid: current_text_sha(root, cid)
            for cid in _leaf_ids([ch])
            if current_text_sha(root, cid) is not None
        }
        path = _chapter_summary_path(root, ch.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {"level": "chapter", "target_id": ch.id, "child_hashes": child_hashes},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    lines = ["# Document map", ""]
    for u in units:
        _render(root, u, 0, lines, folders)
    map_path(root).parent.mkdir(parents=True, exist_ok=True)
    map_path(root).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"units": len(folders), "chapters": len(_chapters(units))}


def _render(root: Path, unit: model.Unit, depth: int, lines: list[str], folders) -> None:
    indent = "  " * depth
    mark = "stale" if _unit_stale(root, unit.id) else "fresh"
    title = unit.title or unit.id
    extra = ""
    if unit.id in folders:
        s = load_summary(folders[unit.id])
        det = s.get("deterministic", {})
        thesis = s.get("semantic", {}).get("main_thesis", "")
        extra = f" — {det.get('chars_with_spaces', 0)} chars; {thesis}".rstrip()
    lines.append(f"{indent}- [{mark}] {title} ({unit.id}){extra}")
    for c in unit.children:
        _render(root, c, depth + 1, lines, folders)


def _unit_stale(root: Path, unit_id: str) -> bool:
    folders = ops.current_folders(root)
    if unit_id not in folders:
        return False
    summary = load_summary(folders[unit_id])
    if not summary:
        return True
    return summary.get("text_sha256") != current_text_sha(root, unit_id)


def _chapter_stale(root: Path, chapter: model.Unit) -> bool:
    if any(_unit_stale(root, cid) for cid in _leaf_ids([chapter])):
        return True
    path = _chapter_summary_path(root, chapter.id)
    if not path.is_file():
        return True
    recorded = json.loads(path.read_text(encoding="utf-8")).get("child_hashes", {})
    current = {
        cid: current_text_sha(root, cid)
        for cid in _leaf_ids([chapter])
        if current_text_sha(root, cid) is not None
    }
    return recorded != current


def stale_report(root: Path) -> dict[str, bool]:
    units = _tree(root)
    report: dict[str, bool] = {}
    for uid in _leaf_ids(units):
        report[uid] = _unit_stale(root, uid)
    for ch in _chapters(units):
        report[ch.id] = _chapter_stale(root, ch)
    report["map"] = any(report.values()) or not map_path(root).is_file()
    return report


def anything_stale(root: Path) -> bool:
    return any(stale_report(root).values())


def require_fresh(root: Path) -> None:
    """Integration-level guard: refuse while any summary or the map is stale."""
    if anything_stale(root):
        raise BlockedError("error.summaries_stale")
