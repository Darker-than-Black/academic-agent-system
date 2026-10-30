"""Human-channel detection and the interactive `rh gate record` flow (02 §9.3)."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from research_harness.gates import briefing, records, requests

_DECISION = {"1": "approved", "2": "rejected", "3": "approved_with_conditions"}

_P = {
    "uk": {
        "decision": "Рішення (1 схвалити / 2 відхилити / 3 схвалити з умовами): ",
        "reason": "Причина: ",
        "conditions": "Умови: ",
        "code": "Код підтвердження ({code_hint}): ",
        "bad_decision": "Введіть 1, 2 або 3.",
        "need_reason": "Для відхилення / умов потрібна причина.",
        "bad_code": "Невірний код. Нічого не записано. Введіть {code}.",
        "changed": "Увага: знімок змінився з моменту запиту; код обчислено для поточного стану.",
        "recorded": "Записано {ap}: {decision}. Поверніться до агента й скажіть «continue».",
        "aborted": "Три невірні спроби коду. Нічого не записано.",
    },
    "en": {
        "decision": "Decision (1 approve / 2 reject / 3 approve with conditions): ",
        "reason": "Reason: ",
        "conditions": "Conditions: ",
        "code": "Confirmation code ({code_hint}): ",
        "bad_decision": "Enter 1, 2 or 3.",
        "need_reason": "A reason is required to reject or set conditions.",
        "bad_code": "Wrong code. Nothing recorded. Enter {code}.",
        "changed": "Note: the snapshot changed since the request; the code is for the current "
        "state.",
        "recorded": "Recorded {ap}: {decision}. Return to the agent and say 'continue'.",
        "aborted": "Three wrong code attempts. Nothing recorded.",
    },
}


def is_human_channel() -> bool:
    if os.environ.get("RH_AGENT_SESSION"):
        return False
    return sys.stdin.isatty() and sys.stdout.isatty()


def confirmation_code(gate: str, manifest_sha256: str) -> str:
    return f"{gate}-{manifest_sha256[-6:]}"


def run_record(
    root: Path,
    gate: str,
    lang: str,
    *,
    prefill: dict[str, Any] | None = None,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
    request_id: str | None = None,
) -> dict[str, Any] | None:
    """Interactive author flow. Returns the recorded approval, or None if aborted."""
    prefill = prefill or {}
    p = _P.get(lang, _P["en"])
    target = requests.current_target(root)
    code = confirmation_code(gate, target["manifest_sha256"])

    output_fn(briefing.render(root, gate, lang))
    if request_id:
        rf = requests.requests_dir(root) / f"{request_id}.json"
        if rf.is_file():
            import json

            old = json.loads(rf.read_text(encoding="utf-8"))["target"]["manifest_sha256"]
            if old != target["manifest_sha256"]:
                output_fn(p["changed"])

    # Decision
    decision = None
    pre = prefill.get("decision")
    while decision is None:
        raw = (pre or input_fn(p["decision"])).strip()
        pre = None
        decision = _DECISION.get(raw)
        if decision is None:
            output_fn(p["bad_decision"])

    # Reason (required for reject / conditions)
    reason = prefill.get("reason") or ""
    if decision in ("rejected", "approved_with_conditions"):
        while not reason.strip():
            reason = input_fn(p["reason"]).strip()
            if not reason:
                output_fn(p["need_reason"])

    conditions = prefill.get("conditions")
    if decision == "approved_with_conditions" and not conditions:
        conditions = input_fn(p["conditions"]).strip()

    # Confirmation code (always typed, max 3 tries)
    for _ in range(3):
        typed = input_fn(p["code"].format(code_hint=code)).strip()
        if typed == code:
            rec = records.record(
                root,
                gate,
                decision=decision,
                reason=reason,
                target=target,
                channel="tty_confirmation",
                conditions=conditions,
                request_id=request_id,
            )
            output_fn(p["recorded"].format(ap=rec["id"], decision=decision))
            return rec
        output_fn(p["bad_code"].format(code=code))
    output_fn(p["aborted"])
    return None
