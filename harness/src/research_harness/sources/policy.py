"""Load the source resource policy and resolve auth from the environment (H8).

Reads ``harness/config/source-policy.yaml`` (data). Auth is resolved by env
VARIABLE NAME only; values are read from the environment and never logged,
stored or returned to callers beyond a ``present`` boolean and the live value
handed straight to a request (NFR-06).
"""

from __future__ import annotations

import os
from functools import cache
from pathlib import Path
from typing import Any

import yaml

_CONFIG = Path(__file__).resolve().parents[3] / "config"


@cache
def load_policy() -> dict[str, Any]:
    raw = (_CONFIG / "source-policy.yaml").read_text(encoding="utf-8")
    return yaml.safe_load(raw) or {}


def resources() -> dict[str, Any]:
    return load_policy().get("resources", {})


def resource(name: str) -> dict[str, Any]:
    res = resources().get(name)
    if res is None:
        raise KeyError(name)
    return res


def is_api(name: str) -> bool:
    return resource(name).get("kind") == "api"


def is_deferred(name: str) -> bool:
    """True when the resource's docs could not be verified (adapter is disabled)."""
    return bool(resource(name).get("docs_unverified"))


def env_value(var_name: str | None) -> str | None:
    """Live value of an env var by name; ``None`` if unset/blank. Never logged."""
    if not var_name:
        return None
    value = os.environ.get(var_name)
    return value or None


def auth_for(name: str) -> dict[str, Any]:
    """Resolve a resource's auth to concrete (unlogged) values plus presence flags.

    Returns keys among: ``api_key``, ``mailto``, ``email`` (live values or None)
    and ``*_present`` booleans. Only variable NAMES come from the policy.
    """
    auth = resource(name).get("auth", {}) or {}
    out: dict[str, Any] = {}
    for kind, field in (
        ("api_key_env", "api_key"),
        ("mailto_env", "mailto"),
        ("email_env", "email"),
    ):
        var = auth.get(kind)
        value = env_value(var)
        out[field] = value
        out[f"{field}_present"] = value is not None
        out[f"{field}_var"] = var
    return out
