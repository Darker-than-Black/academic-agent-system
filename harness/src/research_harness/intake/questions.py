"""Load questions and plan what still needs asking (02 §9.1, FR-44, NFR-15)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from research_harness.intake.conditions import evaluate

_QUESTIONS = Path(__file__).resolve().parents[3] / "intake" / "questions.yaml"
_SHORT_MODES = {"revise", "respond_to_reviewers"}


def load_questions() -> list[dict[str, Any]]:
    data = yaml.safe_load(_QUESTIONS.read_text(encoding="utf-8"))
    return data["questions"]


def core_count() -> int:
    return sum(1 for q in load_questions() if q.get("core"))


def _prefill_value(
    q: dict[str, Any], author_profile: dict[str, Any], previous: dict[str, Any]
) -> Any:
    source = q.get("prefill_from")
    if not source:
        return None, None
    if source.startswith("author.profile."):
        field = source.split(".", 2)[2]
        value = author_profile.get(field)
        if isinstance(value, list):
            value = value[0] if value else None
        if value in (None, "", "unknown"):
            return None, None
        return value, "prefilled_author"
    if source.startswith("previous_intake."):
        qid = source.split(".", 1)[1]
        prev = previous.get(qid)
        value = prev.get("value") if isinstance(prev, dict) else prev
        if value in (None, "", "unknown"):
            return None, None
        return value, "prefilled_previous"
    return None, None


def plan(
    answers: dict[str, Any],
    *,
    author_profile: dict[str, Any] | None = None,
    previous: dict[str, Any] | None = None,
    mode: str = "create",
) -> dict[str, Any]:
    """Return {ask, prefilled, answered}: questions still to ask, with prefills."""
    author_profile = author_profile or {}
    previous = previous or {}
    ask: list[dict[str, Any]] = []
    prefilled: list[dict[str, Any]] = []
    answered: list[str] = []
    for q in load_questions():
        qid = q["id"]
        if qid in answers:
            answered.append(qid)
            continue
        if mode in _SHORT_MODES and not q.get("core"):
            continue
        cond = q.get("condition")
        if cond and not evaluate(cond, answers):
            continue
        value, source = _prefill_value(q, author_profile, previous)
        if value is not None:
            prefilled.append({"id": qid, "value": value, "source": source, "confirm": True})
        else:
            ask.append(q)
    return {"ask": ask, "prefilled": prefilled, "answered": answered}
