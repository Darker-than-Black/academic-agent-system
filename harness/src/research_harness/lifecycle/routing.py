"""Entry routing: `rh start` and `rh continue` (02 §4.2, FR-41)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from research_harness.core.clock import default_clock
from research_harness.core.ids import new_unit_id
from research_harness.intake import answers as intake_answers
from research_harness.intake import questions as intake_questions
from research_harness.lifecycle import stages as stage_model
from research_harness.lifecycle import status as status_mod
from research_harness.state import recovery
from research_harness.workspace import author
from research_harness.workspace.objects import create_object
from research_harness.workspace.workspace import Workspace

_THESIS_SKELETON = [
    ("introduction", {"uk": "Вступ", "en": "Introduction"}),
    ("conclusions", {"uk": "Висновки", "en": "Conclusions"}),
    ("references", {"uk": "Список джерел", "en": "References"}),
]


def _skeleton(kind: str, lang: str) -> list[dict[str, Any]]:
    if kind != "thesis":
        return []
    return [
        {"id": new_unit_id(), "kind": k, "title": name.get(lang, name["en"])}
        for k, name in _THESIS_SKELETON
    ]


def start(
    ws: Workspace, *, title: str, kind: str, mode: str = "create", lang: str = "uk"
) -> dict[str, Any]:
    if mode in ("revise", "respond_to_reviewers"):
        return {"result": "mode_unsupported", "mode": mode}

    candidates = [
        o for o in ws.list_objects() if o.get("title", "").strip().lower() == title.strip().lower()
    ]
    if candidates:
        return {"result": "ambiguous", "candidates": candidates}

    oid, folder = create_object(
        ws,
        title=title,
        kind=kind,
        document_kind=kind,
        structure_units=_skeleton(kind, lang),
        stages=stage_model.initial_states(kind, clock_now=default_clock().now_rfc3339()),
    )
    plan = intake_questions.plan(
        intake_answers.load(folder)["answers"], author_profile=author.read_profile(ws)
    )
    return {
        "result": "created",
        "oid": oid,
        "folder": str(folder),
        "questions": [
            {
                "id": q["id"],
                "text": q["text"].get(lang, q["text"]["en"]),
                "core": q.get("core", False),
            }
            for q in plan["ask"]
        ],
        "prefilled": plan["prefilled"],
    }


def continue_object(root: Path, lang: str = "uk") -> dict[str, Any]:
    """Recovery report (no repair) + status; never changes content."""
    findings = recovery.recover(root, repair=False)
    report = status_mod.build_report(root, lang)
    return {"recovery": findings, "status": report, "next_action": report["next_action"]}
