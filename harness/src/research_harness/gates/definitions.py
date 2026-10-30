"""Load and validate gate definitions (02 §9.3)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from research_harness.core.errors import InvalidInputError
from research_harness.schemas import validate

GATES_DIR = Path(__file__).resolve().parents[3] / "gates"
GATES = ("G0", "G1", "G2", "G3", "GE")


def load_gate(gate: str) -> dict[str, Any]:
    path = GATES_DIR / f"{gate}.yaml"
    if not path.is_file():
        raise InvalidInputError("error.gate_unknown")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    errors = validate("gate-definition", data)
    if errors:
        raise InvalidInputError("error.gate_invalid")
    return data


def load_all() -> dict[str, dict[str, Any]]:
    return {g: load_gate(g) for g in GATES}
