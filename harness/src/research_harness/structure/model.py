"""`structure.yaml` model and label resolution (02 §7.1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

TOP_KINDS = {
    "abstract",
    "introduction",
    "conclusions",
    "references",
    "appendices",
    "section",
    "chapter",
}
CHILD_KINDS = {"subsection", "chapter_conclusions"}

_CONFIG_LABELS = Path(__file__).resolve().parents[3] / "config" / "labels.yaml"


@dataclass
class Unit:
    id: str
    kind: str
    title: str | None = None
    generated: bool = False
    children: list[Unit] = field(default_factory=list)


def load(folder: Path) -> dict[str, Any]:
    text = (folder / "structure.yaml").read_text(encoding="utf-8")
    return yaml.safe_load(text) or {}


def save(folder: Path, data: dict[str, Any]) -> None:
    from research_harness.state.snapshot import atomic_write_bytes

    atomic_write_bytes(
        folder / "structure.yaml",
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False).encode("utf-8"),
    )


def parse_units(data: dict[str, Any]) -> list[Unit]:
    def build(node: dict[str, Any]) -> Unit:
        return Unit(
            id=node["id"],
            kind=node["kind"],
            title=node.get("title"),
            generated=bool(node.get("generated", False)),
            children=[build(c) for c in node.get("children", [])],
        )

    return [build(n) for n in data.get("units", [])]


def dump_units(units: list[Unit]) -> list[dict[str, Any]]:
    def emit(u: Unit) -> dict[str, Any]:
        node: dict[str, Any] = {"id": u.id, "kind": u.kind, "title": u.title}
        if u.generated:
            node["generated"] = True
        if u.children:
            node["children"] = [emit(c) for c in u.children]
        return node

    return [emit(u) for u in units]


def resolve_labels(data: dict[str, Any], main_language: str) -> dict[str, str]:
    """Rule-pack / structure labels if present, else config defaults by language."""
    labels = dict(data.get("labels") or {})
    if "chapter" in labels and "chapter_conclusions" in labels:
        return labels
    defaults = yaml.safe_load(_CONFIG_LABELS.read_text(encoding="utf-8"))
    lang_defaults = defaults.get(main_language) or defaults.get("uk", {})
    for k, v in lang_defaults.items():
        labels.setdefault(k, v)
    return labels


def iter_ids(units: list[Unit]) -> list[str]:
    out: list[str] = []
    for u in units:
        out.append(u.id)
        out.extend(iter_ids(u.children))
    return out
