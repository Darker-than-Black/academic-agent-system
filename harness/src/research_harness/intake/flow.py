"""Intake answer orchestration: record → summary → resolve → checkpoint → G0."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from research_harness.gates.requests import open_request
from research_harness.intake import answers as answers_mod
from research_harness.intake import summary as summary_mod
from research_harness.rules.service import resolve_object
from research_harness.state.store import Store

_G0_BRIEF = {
    "uk": "# G0 — Схвалення анкетування\n\nПерегляньте intake/summary.md: тему, вид документа, "
    "видання, мову та кожне «невідомо» з його наслідком. Запишіть рішення у власному терміналі:\n"
    "  rh --object {oid} gate record G0\n",
    "en": "# G0 — Intake approval\n\nReview intake/summary.md: topic, document kind, venue, "
    "language and each 'unknown' with its consequence. Record the decision in your own terminal:\n"
    "  rh --object {oid} gate record G0\n",
}


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
    import json

    oid = json.loads((root / "object.json").read_text(encoding="utf-8"))["id"]
    brief = _G0_BRIEF.get(lang, _G0_BRIEF["en"]).format(oid=oid)
    return open_request(root, "G0", briefing_text=brief, summary_path="intake/summary.md")
