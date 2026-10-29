"""Role→tier and host→tier→model configuration (02 §10)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from research_harness.core.errors import InvalidInputError
from research_harness.schemas import validate

_CONFIG = Path(__file__).resolve().parents[3] / "config"
UNKNOWN = "unknown"


def load_roles() -> dict[str, str]:
    data = yaml.safe_load((_CONFIG / "roles.yaml").read_text(encoding="utf-8"))
    errors = validate("roles", data)
    if errors:
        raise InvalidInputError("error.model_config_invalid")
    return {k: v for k, v in data.items() if k != "schema_version"}


def load_tiers() -> dict[str, Any]:
    data = yaml.safe_load((_CONFIG / "model-tiers.yaml").read_text(encoding="utf-8"))
    errors = validate("model-tiers", data)
    if errors:
        raise InvalidInputError("error.model_config_invalid")
    return data


def host_from_env(explicit: str | None = None) -> str:
    return os.environ.get("RH_HOST") or explicit or "claude-code"


def tier_for_role(role: str) -> str:
    roles = load_roles()
    if role not in roles:
        raise InvalidInputError("error.model_unknown_role")
    return roles[role]


def resolve(role: str, host: str) -> tuple[str, str | None]:
    """Return (tier, model_id). model_id is None when the tier maps to unknown."""
    tier = tier_for_role(role)
    if tier == "none":
        return tier, None
    tiers = load_tiers()["hosts"].get(host)
    if tiers is None:
        raise InvalidInputError("error.model_unknown_host")
    entry = tiers.get(tier)
    if entry is None or entry.get("model", UNKNOWN) == UNKNOWN:
        return tier, None
    return tier, entry["model"]
