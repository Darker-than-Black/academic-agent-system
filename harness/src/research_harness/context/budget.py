"""Context budgets and the token estimate (FR-48). The estimate method is
recorded in every pack manifest; no truncation — over budget is an error.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_CONFIG = Path(__file__).resolve().parents[3] / "config" / "context-budgets.yaml"


def load_budgets() -> dict[str, Any]:
    return yaml.safe_load(_CONFIG.read_text(encoding="utf-8"))


def method() -> str:
    return load_budgets().get("method", "chars_div_4")


def budget_for(role: str) -> int:
    return int(load_budgets().get("roles", {}).get(role, 8000))


def estimate_tokens(text: str) -> int:
    """char/4 heuristic (the method recorded in the manifest)."""
    return len(text) // 4
