"""Migration registry keyed by (schema, from, to). Each migration is a pure
function old record → new record (02 §11)."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Migration:
    schema: str
    filename: str  # managed file at the object root, e.g. "object.json"
    from_v: str
    to_v: str
    fn: Callable[[dict[str, Any]], dict[str, Any]]
    description: str


_REGISTRY: list[Migration] = []


def register(m: Migration) -> None:
    _REGISTRY.append(m)


def all_migrations() -> list[Migration]:
    return list(_REGISTRY)


def chain(schema: str, from_v: str, to_v: str) -> list[Migration]:
    """Ordered migrations taking ``schema`` from ``from_v`` to ``to_v`` (empty if none)."""
    by_from = {m.from_v: m for m in _REGISTRY if m.schema == schema}
    out: list[Migration] = []
    cur = from_v
    seen: set[str] = set()
    while cur != to_v:
        m = by_from.get(cur)
        if m is None or cur in seen:
            return []
        out.append(m)
        seen.add(cur)
        cur = m.to_v
    return out


def targets() -> dict[str, str]:
    """Map managed filename → schema for every registered migration."""
    return {m.filename: m.schema for m in _REGISTRY}


def _rename_field(old: str, new: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def fn(doc: dict[str, Any]) -> dict[str, Any]:
        out = dict(doc)
        if old in out:
            out[new] = out.pop(old)
        return out

    return fn


_TEST_MIGRATION = Migration(
    schema="migrate-test",
    filename="migrate-test.json",
    from_v="0.2",
    to_v="0.3",
    fn=_rename_field("old_field", "new_field"),
    description="rename old_field → new_field",
)


def ensure_test_migration() -> None:
    """Register the test-only migration (idempotent); used under RH_TEST_MODE."""
    if not any(m.schema == "migrate-test" for m in _REGISTRY):
        register(_TEST_MIGRATION)


# Test-only migration is registered only under RH_TEST_MODE=1 (02 §11): it
# renames one field in a dedicated test document, never a real object schema.
if os.environ.get("RH_TEST_MODE") == "1":
    ensure_test_migration()
