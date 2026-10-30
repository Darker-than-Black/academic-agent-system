"""Rule composition and resolution (02 §8.3–§8.5, FR-27, T28, T29)."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from research_harness.core.clock import default_clock
from research_harness.rules.freshness import classify
from research_harness.rules.loader import Pack

_SEV_RANK = {"info": 0, "minor": 1, "major": 2, "blocker": 3}
_RANK_SEV = {v: k for k, v in _SEV_RANK.items()}


@dataclass
class ResolvedStack:
    packs: list[dict[str, Any]] = field(default_factory=list)
    rules: list[dict[str, Any]] = field(default_factory=list)
    findings: list[dict[str, Any]] = field(default_factory=list)

    def export_blocked(self) -> bool:
        return any(f.get("blocks_verified_export") for f in self.findings)


def _cap_severity(rule: dict[str, Any]) -> str:
    sev = rule.get("severity", "info")
    if (
        rule.get("source", {}).get("evidence_level") == "secondary"
        and _SEV_RANK[sev] > _SEV_RANK["major"]
    ):
        return "major"  # 02 §8.3.7
    return sev


def _highest(severities: list[str]) -> str:
    return _RANK_SEV[max(_SEV_RANK[s] for s in severities)]


def _combine(compare: str, values: list[Any]) -> tuple[Any, bool]:
    """Return (effective_value, ok). ok=False means an unresolvable conflict."""
    if compare == "min":
        return max(values), True
    if compare == "max":
        return min(values), True
    if compare in ("required", "forbidden"):
        return any(bool(v) for v in values), True
    if compare == "one_of":
        sets = [set(v) for v in values]
        return sorted(set.intersection(*sets)), True
    if compare == "equals":
        uniq = {json.dumps(v, sort_keys=True) for v in values}
        return (values[0], True) if len(uniq) == 1 else (None, False)
    return None, True


def _finding(
    check_id: str, severity: str, key: str, reason: str, *, export_block: bool = False
) -> dict[str, Any]:
    f = {"check_id": check_id, "severity": severity, "key": key, "at": "A0", "reason": reason}
    if export_block:
        f["blocks_verified_export"] = True
    return f


def resolve(packs: list[Pack], *, at: str | None = None) -> ResolvedStack:
    stack = ResolvedStack()
    group: dict[str, list[tuple[Pack, dict[str, Any]]]] = defaultdict(list)
    for p in packs:
        stack.packs.append(
            {
                "id": p.id,
                "version": p.version,
                "layer": p.layer,
                "status": p.status,
                "sha256": p.sha256,
            }
        )
        for r in p.rules:
            group[r["key"]].append((p, r))

    for key, members in group.items():
        core = [(p, r) for p, r in members if not r.get("overridable", True)]
        if core:
            core_p, core_r = core[0]
            stack.rules.append(_entry(core_p, core_r, True, at))
            for p, r in members:
                if r["id"] != core_r["id"]:
                    stack.rules.append(_entry(p, r, False, at, overridden_by=core_r["id"]))
                    stack.findings.append(
                        _finding(
                            "rules.core_override_attempt",
                            "major",
                            key,
                            f"{r['id']} tries to override core {core_r['id']}",
                        )
                    )
            continue

        kind = members[0][1]["kind"]
        if kind in ("structure", "format"):
            top_layer = max(p.layer for p, _ in members)
            top = [(p, r) for p, r in members if p.layer == top_layer]
            if len({r["id"] for _, r in top}) > 1:
                stack.findings.append(
                    _finding("rules.conflict", "blocker", key, f"same-layer conflict on {key}")
                )
                for p, r in members:
                    stack.rules.append(_entry(p, r, False, at))
            else:
                win_p, win_r = top[0]
                stack.rules.append(_entry(win_p, win_r, True, at))
                for p, r in members:
                    if r["id"] != win_r["id"]:
                        stack.rules.append(_entry(p, r, False, at, overridden_by=win_r["id"]))
        elif kind in ("integrity", "counting"):
            compares = {r["compare"] for _, r in members if "compare" in r}
            eff_value: Any = None
            ok = True
            if len(compares) > 1:
                ok = False
                stack.findings.append(
                    _finding("rules.conflict", "blocker", key, f"incomparable rules on {key}")
                )
            elif compares:
                eff_value, ok = _combine(compares.pop(), [r["value"] for _, r in members])
                if not ok:
                    stack.findings.append(
                        _finding("rules.conflict", "blocker", key, f"conflicting equals on {key}")
                    )
            eff_sev = _highest([_cap_severity(r) for _, r in members])
            for p, r in members:
                stack.rules.append(
                    _entry(
                        p, r, True, at, eff_severity=eff_sev, eff_value=eff_value if ok else None
                    )
                )
        else:  # process: union
            for p, r in members:
                stack.rules.append(_entry(p, r, True, at))

    _apply_freshness(stack)
    return stack


def _entry(
    pack: Pack,
    rule: dict[str, Any],
    effective: bool,
    at: str | None,
    *,
    overridden_by: str | None = None,
    eff_severity: str | None = None,
    eff_value: Any = None,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "rule_id": rule["id"],
        "pack": pack.id,
        "key": rule["key"],
        "effective": effective,
        "freshness": classify(rule, at),
        "effective_severity": eff_severity or _cap_severity(rule),
    }
    if overridden_by:
        entry["overridden_by"] = overridden_by
    value = eff_value if eff_value is not None else rule.get("value")
    if value is not None:
        entry["effective_value"] = value
    return entry


def _apply_freshness(stack: ResolvedStack) -> None:
    for entry in stack.rules:
        if not entry["effective"]:
            continue
        if entry["freshness"] == "expired":
            stack.findings.append(
                _finding(
                    "rules.expired",
                    "major",
                    entry["key"],
                    f"rule {entry['rule_id']} is expired; dependent checks return unknown",
                    export_block=True,
                )
            )
        elif entry["freshness"] == "not_yet_valid":
            entry["effective"] = False
            stack.findings.append(
                _finding(
                    "rules.not_yet_valid",
                    "info",
                    entry["key"],
                    f"rule {entry['rule_id']} is not yet valid",
                )
            )


def build_resolved_stack(stack: ResolvedStack, inputs: list[dict[str, Any]]) -> dict[str, Any]:
    """A schema-valid profiles/resolved-stack.json document (02 §8.5)."""
    return {
        "schema_version": "0.2",
        "resolved_at": default_clock().now_rfc3339(),
        "inputs": inputs,
        "packs": stack.packs,
        "rules": stack.rules,
        "findings": [f["check_id"] for f in stack.findings],
    }
