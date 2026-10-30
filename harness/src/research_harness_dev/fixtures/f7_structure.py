"""F7 structural skeleton (M1-07, T50). Placeholder text only; synthetic (H6)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from research_harness.structure import ops
from research_harness.workspace.objects import create_object
from research_harness.workspace.workspace import Workspace

INTRO = "U-00000001"
CH1, CH2, CH3 = "U-00000002", "U-00000003", "U-00000004"
CONCL, REFS, APP = "U-00000005", "U-00000006", "U-00000007"
CH1_SUBS = ["U-00000011", "U-00000012", "U-00000013", "U-00000014"]
CH1_CONCL = "U-00000015"
CH2_SUBS = ["U-00000021", "U-00000022", "U-00000023"]
CH2_CONCL = "U-00000024"
CH3_SUBS = ["U-00000031", "U-00000032", "U-00000033"]
CH3_CONCL = "U-00000034"


def _chapter(cid: str, title: str, subs: list[str], concl: str) -> dict[str, Any]:
    children = [
        {"id": s, "kind": "subsection", "title": f"Підрозділ {i}"} for i, s in enumerate(subs, 1)
    ]
    children.append({"id": concl, "kind": "chapter_conclusions", "title": None})
    return {"id": cid, "kind": "chapter", "title": title, "children": children}


def build_f7_structure(dest: Path) -> Path:
    ws = Workspace.init(dest)
    units = [
        {"id": INTRO, "kind": "introduction", "title": "Вступ"},
        _chapter(CH1, "Перший розділ", CH1_SUBS, CH1_CONCL),
        _chapter(CH2, "Другий розділ", CH2_SUBS, CH2_CONCL),
        _chapter(CH3, "Третій розділ", CH3_SUBS, CH3_CONCL),
        {"id": CONCL, "kind": "conclusions", "title": "Висновки"},
        {"id": REFS, "kind": "references", "title": "Список джерел", "generated": True},
        {"id": APP, "kind": "appendices", "title": "Додатки"},
    ]
    _oid, folder = create_object(
        ws,
        title="Дисертація",
        kind="thesis",
        languages={"main": "uk", "abstracts": ["uk"]},
        structure_units=units,
    )
    ops.sync(folder, "uk")
    return folder


# Depth-1 article: the same code path (ADR-019 p.2).
ART_SECS = ["U-10000001", "U-10000002", "U-10000003"]


def build_f7_article(dest: Path) -> Path:
    ws = Workspace.init(dest)
    units = [
        {"id": s, "kind": "section", "title": f"Секція {i}"} for i, s in enumerate(ART_SECS, 1)
    ]
    _oid, folder = create_object(
        ws,
        title="Стаття",
        kind="article",
        languages={"main": "uk", "abstracts": ["uk"]},
        structure_units=units,
    )
    ops.sync(folder, "uk")
    return folder
