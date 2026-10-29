"""Stage definitions as data; initial states for a new object (02 §4.2)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_DIR = Path(__file__).resolve().parent
_FILES = {"article": "article_stages.yaml", "thesis": "thesis_stages.yaml"}


def load_stages(kind: str) -> list[dict[str, Any]]:
    fname = _FILES.get(kind, _FILES["article"])
    return yaml.safe_load((_DIR / fname).read_text(encoding="utf-8"))["stages"]


def stage_ids(kind: str) -> list[str]:
    return [s["id"] for s in load_stages(kind)]


def stage_name(kind: str, sid: str, lang: str) -> str:
    for s in load_stages(kind):
        if s["id"] == sid:
            return s["name"].get(lang, s["name"].get("en", sid))
    return sid


def gates_for(kind: str) -> dict[str, str]:
    """Map gate id -> the stage whose completion it guards."""
    return {s["gate"]: s["id"] for s in load_stages(kind) if s.get("gate")}


def initial_states(kind: str, *, clock_now: str) -> dict[str, Any]:
    """A0/T0 active, the rest pending. not_applicable/terminal applied later."""
    ids = stage_ids(kind)
    states: dict[str, Any] = {}
    for i, sid in enumerate(ids):
        states[sid] = {"state": "active" if i == 0 else "pending", "updated_at": clock_now}
    return states
