"""Structure operations with crash-safe two-phase folder renames (02 §7.3)."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from research_harness.core.ids import new_unit_id
from research_harness.state.faults import fault_point
from research_harness.state.snapshot import atomic_write_bytes
from research_harness.state.store import Store
from research_harness.structure import model
from research_harness.structure.model import Unit
from research_harness.structure.naming import compute_paths

HUMAN = {"kind": "human", "name": "rh", "version": "0.1.0"}
_TEMPLATES = Path(__file__).resolve().parent / "templates"
_JOURNAL = ".rh/structure-journal.json"


# --- unit folder discovery / materialization ------------------------------
def _front_matter(text: str) -> dict[str, Any]:
    import yaml

    if not text.startswith("---"):
        return {}
    _, _, rest = text.partition("\n")
    body, sep, _ = rest.partition("\n---")
    if not sep:
        return {}
    data = yaml.safe_load(body)
    return data if isinstance(data, dict) else {}


def current_folders(root: Path) -> dict[str, Path]:
    """unit id -> its folder, by scanning manuscript/** for text.md front matter."""
    out: dict[str, Path] = {}
    man = root / "manuscript"
    if not man.is_dir():
        return out
    for text in man.rglob("text.md"):
        fid = _front_matter(text.read_text(encoding="utf-8")).get("id")
        if fid:
            out[fid] = text.parent
    return out


def materialize_unit(folder: Path, unit: Unit) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    tpl = (_TEMPLATES / "text.md").read_text(encoding="utf-8")
    (folder / "text.md").write_text(
        tpl.format(id=unit.id, title=unit.title or "", kind=unit.kind), encoding="utf-8"
    )
    for name in ("brief.md", "summary.md", "claims.json"):
        content = (_TEMPLATES / name).read_text(encoding="utf-8").format(id=unit.id)
        (folder / name).write_text(content, encoding="utf-8")


# --- crash-safe sync -------------------------------------------------------
def _rel(root: Path, p: Path) -> str:
    return p.relative_to(root).as_posix()


def complete_journal(root: Path) -> bool:
    """Finish an interrupted rename (called by recovery). True if one was found."""
    jpath = root / _JOURNAL
    if not jpath.exists():
        return False
    moves = json.loads(jpath.read_text(encoding="utf-8"))["moves"]
    # Shallowest final first, so parents exist before children.
    for mv in sorted(moves, key=lambda m: m["final"].count("/")):
        final = root / mv["final"]
        if final.exists():
            continue
        temp, src = root / mv["temp"], root / mv["src"]
        source = temp if temp.exists() else (src if src.exists() else None)
        if source is None:
            continue
        final.parent.mkdir(parents=True, exist_ok=True)
        os.replace(source, final)
    jpath.unlink(missing_ok=True)
    return True


def sync_folders(root: Path, units: list[Unit], labels: dict[str, str]) -> dict[str, Any]:
    desired = compute_paths(units, labels)  # id -> rel
    current = current_folders(root)
    renames = []
    for uid, rel in desired.items():
        if uid in current and _rel(root, current[uid]) != rel:
            renames.append(
                {
                    "id": uid,
                    "src": _rel(root, current[uid]),
                    "temp": f"manuscript/.rhtmp-{uid}",
                    "final": rel,
                }
            )
    if renames:
        jpath = root / _JOURNAL
        atomic_write_bytes(jpath, (json.dumps({"moves": renames}) + "\n").encode("utf-8"))
        # Phase 1: deepest current first -> flat temp (detaches children before parents).
        for mv in sorted(renames, key=lambda m: m["src"].count("/"), reverse=True):
            os.replace(root / mv["src"], root / mv["temp"])
        fault_point("structure_rename_phase2")
        # Phase 2: shallowest final first -> final location.
        for mv in sorted(renames, key=lambda m: m["final"].count("/")):
            final = root / mv["final"]
            final.parent.mkdir(parents=True, exist_ok=True)
            os.replace(root / mv["temp"], final)
        jpath.unlink(missing_ok=True)

    # Create folders for units that have no folder yet.
    current = current_folders(root)
    created = []
    by_id = {u.id: u for u in _flatten(units)}
    for uid, rel in desired.items():
        if uid not in current:
            materialize_unit(root / rel, by_id[uid])
            created.append(rel)
    return {"renamed": len(renames), "created": created}


def _flatten(units: list[Unit]) -> list[Unit]:
    out: list[Unit] = []
    for u in units:
        out.append(u)
        out.extend(_flatten(u.children))
    return out


# --- high-level operations -------------------------------------------------
def _apply(
    root: Path, main_language: str, mutate: Callable[[list[Unit]], None], note: str
) -> dict[str, Any]:
    data = model.load(root)
    units = model.parse_units(data)
    mutate(units)
    data["units"] = model.dump_units(units)
    model.save(root, data)
    labels = model.resolve_labels(data, main_language)
    summary = sync_folders(root, units, labels)
    Store(root).checkpoint(by="human", note=note)
    return summary


def renumber(root: Path, main_language: str = "uk") -> dict[str, Any]:
    return _apply(root, main_language, lambda units: None, "structure renumber")


def retitle(root: Path, unit_id: str, title: str, main_language: str = "uk") -> dict[str, Any]:
    def mut(units: list[Unit]) -> None:
        for u in _flatten(units):
            if u.id == unit_id:
                u.title = title

    return _apply(root, main_language, mut, f"structure retitle {unit_id}")


def add_unit(
    root: Path,
    *,
    kind: str,
    title: str | None,
    parent_id: str | None = None,
    index: int | None = None,
    main_language: str = "uk",
) -> str:
    new_id = new_unit_id(set(model.iter_ids(model.parse_units(model.load(root)))))
    unit = Unit(id=new_id, kind=kind, title=title)

    def mut(units: list[Unit]) -> None:
        target = units
        if parent_id is not None:
            for u in _flatten(units):
                if u.id == parent_id:
                    target = u.children
                    break
        target.insert(index if index is not None else len(target), unit)

    _apply(root, main_language, mut, f"structure add {new_id}")
    return new_id


def move(root: Path, unit_id: str, new_index: int, main_language: str = "uk") -> dict[str, Any]:
    def mut(units: list[Unit]) -> None:
        _reorder(units, unit_id, new_index)

    return _apply(root, main_language, mut, f"structure move {unit_id}")


def _reorder(units: list[Unit], unit_id: str, new_index: int) -> bool:
    for i, u in enumerate(units):
        if u.id == unit_id:
            units.insert(new_index, units.pop(i))
            return True
        if _reorder(u.children, unit_id, new_index):
            return True
    return False


def remove(root: Path, unit_id: str, main_language: str = "uk") -> dict[str, Any]:
    folders = current_folders(root)
    victim = folders.get(unit_id)

    def mut(units: list[Unit]) -> None:
        _drop(units, unit_id)

    if victim and victim.is_dir():
        import shutil

        shutil.rmtree(victim)
    return _apply(root, main_language, mut, f"structure remove {unit_id}")


def _drop(units: list[Unit], unit_id: str) -> bool:
    for i, u in enumerate(units):
        if u.id == unit_id:
            units.pop(i)
            return True
        if _drop(u.children, unit_id):
            return True
    return False


def sync(root: Path, main_language: str = "uk") -> dict[str, Any]:
    """Make folders and front matter match structure.yaml (02 §7.2 'sync')."""
    data = model.load(root)
    units = model.parse_units(data)
    labels = model.resolve_labels(data, main_language)
    summary = sync_folders(root, units, labels)
    # Repair front-matter titles/kinds to match structure.yaml.
    folders = current_folders(root)
    for u in _flatten(units):
        folder = folders.get(u.id)
        if folder is None:
            continue
        tpl = (_TEMPLATES / "text.md").read_text(encoding="utf-8")
        existing = (folder / "text.md").read_text(encoding="utf-8")
        _, _, after = existing.partition("\n---\n")
        header = tpl.format(id=u.id, title=u.title or "", kind=u.kind)
        (folder / "text.md").write_text(header + (after or "\n"), encoding="utf-8")
    Store(root).checkpoint(by="human", note="structure sync")
    return summary
