"""Render intake/summary.md in the author's ui_language (02 §9.1)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from research_harness.intake.questions import load_questions
from research_harness.state.snapshot import atomic_write_bytes

_HEAD = {"uk": "# Підсумок анкетування\n", "en": "# Intake summary\n"}
_ANSWERS = {"uk": "## Відповіді\n", "en": "## Answers\n"}
_UNKNOWNS = {"uk": "## Невідоме та наслідки\n", "en": "## Unknowns and consequences\n"}
_BLOCKS = {"uk": "блокує", "en": "blocks"}


def render(root: Path, data: dict[str, Any], lang: str = "uk") -> Path:
    by_id = {q["id"]: q for q in load_questions()}
    lines = [_HEAD.get(lang, _HEAD["en"]), "", _ANSWERS.get(lang, _ANSWERS["en"])]
    for qid, entry in data["answers"].items():
        q = by_id.get(qid, {})
        text = q.get("text", {}).get(lang, qid)
        lines.append(f"- **{qid}** {text} — `{entry['value']}` ({entry['source']})")
    consequences = data.get("consequences", [])
    if consequences:
        lines += ["", _UNKNOWNS.get(lang, _UNKNOWNS["en"])]
        for c in consequences:
            blocks = ", ".join(c["blocks"]) or "—"
            lines.append(
                f"- **{c['question']}**: {c['note']} ({_BLOCKS.get(lang, 'blocks')}: {blocks})"
            )
    out = root / "intake" / "summary.md"
    atomic_write_bytes(out, ("\n".join(lines) + "\n").encode("utf-8"))
    return out
