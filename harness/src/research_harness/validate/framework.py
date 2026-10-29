"""Check registry and finding model (02 §9.4)."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any, Protocol

Finding = dict[str, Any]

SEVERITIES = ("blocker", "major", "minor", "info")


def finding(
    *,
    check_id: str,
    severity: str,
    reason: str,
    ref: str | None = None,
    unit_id: str | None = None,
    locator: str | None = None,
    rule_id: str | None = None,
    observed: Any = None,
    expected: Any = None,
    proposed_action: str = "",
) -> Finding:
    """Build a finding dict (the subset of 02 §9.4 available before an id is allocated)."""
    if severity not in SEVERITIES:
        raise ValueError(f"invalid severity: {severity!r}")
    location: dict[str, Any] = {}
    if ref is not None:
        location["ref"] = ref
    if unit_id is not None:
        location["unit_id"] = unit_id
    if locator is not None:
        location["locator"] = locator
    out: Finding = {
        "check_id": check_id,
        "severity": severity,
        "reason": reason,
        "location": location,
        "proposed_action": proposed_action,
    }
    if rule_id is not None:
        out["rule_id"] = rule_id
    if observed is not None:
        out["observed"] = observed
    if expected is not None:
        out["expected"] = expected
    return out


def has_blocker(findings: Iterable[Finding]) -> bool:
    return any(f.get("severity") == "blocker" for f in findings)


@dataclass
class ValidationContext:
    """Inputs a check runs against. Later cards populate it from the snapshot."""

    records: dict[str, Any] = field(default_factory=dict)  # ref -> record
    known_refs: set[str] = field(default_factory=set)  # resolvable artifact refs
    extra: dict[str, Any] = field(default_factory=dict)


class Check(Protocol):
    id: str
    version: str
    scope: str

    def __call__(self, ctx: ValidationContext) -> list[Finding]: ...


@dataclass
class _Registered:
    id: str
    version: str
    scope: str
    func: Callable[[ValidationContext], list[Finding]]


class CheckRegistry:
    def __init__(self) -> None:
        self._checks: list[_Registered] = []

    def register(
        self, *, id: str, version: str, scope: str
    ) -> Callable[
        [Callable[[ValidationContext], list[Finding]]], Callable[[ValidationContext], list[Finding]]
    ]:
        def deco(
            func: Callable[[ValidationContext], list[Finding]],
        ) -> Callable[[ValidationContext], list[Finding]]:
            self._checks.append(_Registered(id, version, scope, func))
            return func

        return deco

    def scopes(self) -> set[str]:
        return {c.scope for c in self._checks}

    def for_scopes(self, scopes: Iterable[str]) -> list[_Registered]:
        wanted = set(scopes)
        if "all" in wanted:
            return list(self._checks)
        return [c for c in self._checks if c.scope in wanted]


registry = CheckRegistry()


def run_checks(scopes: Iterable[str], ctx: ValidationContext) -> list[Finding]:
    """Run every registered check whose scope is requested; collect findings."""
    findings: list[Finding] = []
    for check in registry.for_scopes(scopes):
        findings.extend(check.func(ctx))
    return findings
