"""Render an approval briefing in the author's ui_language (02 §9.3 layout)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_harness.gates.definitions import load_gate

_L = {
    "uk": {
        "deciding": "Що ви вирішуєте",
        "approving": "Що схвалюється",
        "check": "Що перевірити",
        "consequences": "Якщо ви схвалюєте / відхиляєте / схвалюєте з умовами",
        "reversible": "Чи можна змінити пізніше",
        "how": "Як записати рішення",
        "steps": (
            "  1. Відкрийте власний термінал (не оболонку агента).\n"
            "  2. Виконайте:  rh --object {oid} gate record {gate}\n"
            "  3. rh покаже цей підсумок і спитає по черзі: рішення (1 схвалити / 2 відхилити / "
            "3 схвалити з умовами), причину (для 2 і 3) та код підтвердження {gate}-<6 hex>.\n"
            "  4. Після запису поверніться до агента й скажіть «continue»."
        ),
        "topic": "Тема",
        "doc_kind": "Вид документа",
        "venue": "Видання",
        "language": "Мова",
        "unknowns": "Невідоме та наслідки",
        "summary_link": "Підсумок анкетування",
    },
    "en": {
        "deciding": "What you are deciding",
        "approving": "What is being approved",
        "check": "What to check",
        "consequences": "If you approve / reject / approve with conditions",
        "reversible": "Can it be changed later",
        "how": "How to record the decision",
        "steps": (
            "  1. Open your own terminal (not the agent's shell).\n"
            "  2. Run:  rh --object {oid} gate record {gate}\n"
            "  3. rh shows this summary and asks, one at a time: decision (1 approve / 2 reject / "
            "3 approve with conditions), reason (for 2 and 3) and the confirmation code "
            "{gate}-<6 hex>.\n"
            "  4. After recording, return to the agent and say 'continue'."
        ),
        "topic": "Topic",
        "doc_kind": "Document kind",
        "venue": "Venue",
        "language": "Language",
        "unknowns": "Unknowns and consequences",
        "summary_link": "Intake summary",
    },
}


def _text(node: dict[str, Any], lang: str) -> str:
    return node.get(lang, node.get("en", ""))


def _g0_body(root: Path, lang: str, lbl: dict[str, str]) -> str:
    obj = json.loads((root / "object.json").read_text(encoding="utf-8"))
    ans_path = root / "intake" / "answers.json"
    answers = (
        json.loads(ans_path.read_text(encoding="utf-8"))["answers"] if ans_path.is_file() else {}
    )

    def val(qid: str) -> str:
        return answers.get(qid, {}).get("value", "—") if isinstance(answers.get(qid), dict) else "—"

    lines = [
        f"- {lbl['topic']}: {val('Q1')}",
        f"- {lbl['doc_kind']}: {obj.get('document_kind', val('Q2'))}",
        f"- {lbl['venue']}: {val('Q4')}",
        f"- {lbl['language']}: {obj.get('languages', {}).get('main', val('Q3'))}",
    ]
    unknowns = (
        [c for c in json.loads(ans_path.read_text(encoding="utf-8")).get("consequences", [])]
        if ans_path.is_file()
        else []
    )
    if unknowns:
        lines.append(f"- {lbl['unknowns']}:")
        for c in unknowns:
            blocks = ", ".join(c["blocks"]) or "—"
            lines.append(f"    - {c['question']}: {c['note']} ({blocks})")
    lines.append(f"- {lbl['summary_link']}: intake/summary.md")
    return "\n".join(lines)


def render(root: Path, gate: str, lang: str) -> str:
    gd = load_gate(gate)
    lbl = _L.get(lang, _L["en"])
    obj = json.loads((root / "object.json").read_text(encoding="utf-8"))
    oid = obj["id"]
    title = obj.get("title", oid)

    approving = _g0_body(root, lang, lbl) if gate == "G0" else f"- {_text(gd['purpose'], lang)}"
    checklist = "\n".join(f"- {_text(item, lang)}" for item in gd["what_to_check"])
    consequences = "\n".join(
        [
            f"- ✓ {_text(gd['if_approved'], lang)}",
            f"- ✗ {_text(gd['if_rejected'], lang)}",
            f"- ± {_text(gd['if_conditions'], lang)}",
        ]
    )
    return (
        f"# {_text(gd['title'], lang)} — {title}\n\n"
        f"## {lbl['deciding']}\n{_text(gd['purpose'], lang)}\n\n"
        f"## {lbl['approving']}\n{approving}\n\n"
        f"## {lbl['check']}\n{checklist}\n\n"
        f"## {lbl['consequences']}\n{consequences}\n\n"
        f"## {lbl['reversible']}\n{_text(gd['reversible'], lang)}\n\n"
        f"## {lbl['how']}\n{lbl['steps'].format(oid=oid, gate=gate)}\n"
    )
