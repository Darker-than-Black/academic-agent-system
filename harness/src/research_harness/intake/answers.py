"""Store intake answers; compute consequences of unknowns (02 §9.1, FR-01/26)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_harness.core.clock import default_clock
from research_harness.core.errors import InvalidInputError
from research_harness.intake.questions import load_questions
from research_harness.state.snapshot import atomic_write_bytes

HUMAN = {"kind": "human", "name": "rh", "version": "0.1.0"}
UNKNOWN = "unknown"


def answers_path(root: Path) -> Path:
    return root / "intake" / "answers.json"


def load(root: Path) -> dict[str, Any]:
    p = answers_path(root)
    if p.is_file():
        return json.loads(p.read_text(encoding="utf-8"))
    return {
        "schema_version": "0.2",
        "id": "intake",
        "created_at": default_clock().now_rfc3339(),
        "producer": HUMAN,
        "mode": "create",
        "answers": {},
        "consequences": [],
    }


def _validate(q: dict[str, Any], value: Any) -> Any:
    qtype = q["type"]
    if value == UNKNOWN:
        return UNKNOWN
    if qtype == "choice":
        if value not in (q.get("options") or []):
            raise InvalidInputError("error.intake_bad_value")
    elif qtype == "bool":
        if isinstance(value, str):
            value = value.lower() in ("true", "1", "yes", "так")
        if not isinstance(value, bool):
            raise InvalidInputError("error.intake_bad_value")
    elif qtype == "multi":
        if not isinstance(value, list):
            raise InvalidInputError("error.intake_bad_value")
    return value


def _consequences(answers: dict[str, Any], lang: str) -> list[dict[str, Any]]:
    by_id = {q["id"]: q for q in load_questions()}
    out: list[dict[str, Any]] = []
    for qid, entry in answers.items():
        if entry.get("value") != UNKNOWN:
            continue
        uc = by_id[qid]["unknown_consequence"]
        out.append(
            {
                "question": qid,
                "blocks": uc.get("blocks", []),
                "unknown_checks": uc.get("unknown_checks", []),
                "note": uc["note"].get(lang, uc["note"].get("en", "")),
            }
        )
    return out


def record(
    root: Path, qid: str, value: Any, *, source: str = "asked", lang: str = "uk"
) -> dict[str, Any]:
    by_id = {q["id"]: q for q in load_questions()}
    if qid not in by_id:
        raise InvalidInputError("error.intake_unknown_question")
    value = _validate(by_id[qid], value)
    data = load(root)
    data["answers"][qid] = {"value": value, "source": source, "confirmed": source == "asked"}
    data["consequences"] = _consequences(data["answers"], lang)
    atomic_write_bytes(
        answers_path(root), (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )
    return data


def missing_core(root: Path) -> list[str]:
    data = load(root)
    return [q["id"] for q in load_questions() if q.get("core") and q["id"] not in data["answers"]]
