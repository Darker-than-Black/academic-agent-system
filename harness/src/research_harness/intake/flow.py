"""Intake answer orchestration: record → summary → resolve → checkpoint → G0."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from research_harness.gates.requests import request_gate
from research_harness.intake import answers as answers_mod
from research_harness.intake import summary as summary_mod
from research_harness.rules.service import resolve_object
from research_harness.state.store import Store


def apply_answer(
    root: Path, qid: str, value: Any, *, source: str = "asked", lang: str = "uk"
) -> dict[str, Any]:
    data = answers_mod.record(root, qid, value, source=source, lang=lang)
    summary_mod.render(root, data, lang)
    resolve_object(root)
    Store(root).checkpoint(by="human", note=f"intake {qid}")
    ar_id = open_g0(root, lang)
    return {"answers": data, "g0_request": ar_id, "consequences": data["consequences"]}


def open_g0(root: Path, lang: str) -> str:
    return request_gate(root, "G0", lang)
