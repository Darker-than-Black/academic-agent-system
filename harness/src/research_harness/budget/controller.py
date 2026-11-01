"""Budget state and the pre-call cost guard (models-budget.md §Invariants).

The controller is pure and side-effect free apart from reading the object's
``budget.yaml`` and ``.rh/`` logs. It never calls a model or a host adapter.

Rules implemented (models-budget.md):
- Usage is computed from ``.rh/model-calls.jsonl`` (and, when present, an
  external-requests log). Any contributing value of ``"unknown"`` makes that
  total ``"unknown"`` — never ``0`` (NFR-05, invariant 3).
- A limit at >= 100% is ``budget.exhausted`` (blocker): the task must stop with
  partial artifacts. 50% and 80% crossings are info findings (invariant 5, #22).
- Paid calls are disabled by default; a paid call is blocked unless
  ``paid_calls: enabled`` with an ``enabled_by`` approval id (ADR-017/ADR-021,
  invariant 4).
- Any ``unknown`` usage makes the overall state ``unknown`` (never ``ok``); a
  known breach outranks it as ``exhausted``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from research_harness.models.calls import calls_path

UNKNOWN = "unknown"

# Limit keys, each paired with the model-call fields that feed it.
LIMIT_KEYS: tuple[str, ...] = (
    "model_calls",
    "tokens",
    "cost",
    "wall_time_s",
    "external_requests",
)

DEFAULT_THRESHOLDS: tuple[float, ...] = (0.5, 0.8, 1.0)

Number = int | float


def budget_path(root: Path) -> Path:
    return root / "budget.yaml"


def load_budget(root: Path) -> dict[str, Any] | None:
    """Read the object's ``budget.yaml`` (``None`` if there is none)."""
    path = budget_path(root)
    if not path.is_file():
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8")) or None


def _accumulate(total: Number | str, value: Any) -> Number | str:
    """Add ``value`` to a running total, propagating ``unknown`` (NFR-05)."""
    if total == UNKNOWN or value == UNKNOWN or value is None:
        return UNKNOWN
    try:
        return total + (value if isinstance(value, (int, float)) else float(value))
    except (TypeError, ValueError):
        return UNKNOWN


def usage_from_calls(root: Path) -> dict[str, Number | str]:
    """Aggregate recorded usage per limit key from the model-call log.

    ``model_calls`` is a count and is always known. ``tokens`` / ``cost`` /
    ``wall_time_s`` propagate ``unknown`` from any contributing record.
    ``external_requests`` reads an optional ``.rh/external-requests.jsonl``; with
    no such log it is ``unknown`` (missing telemetry, not zero).
    """
    path = calls_path(root)
    model_calls = 0
    tokens: Number | str = 0
    cost: Number | str = 0
    wall: Number | str = 0
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            model_calls += 1
            tokens = _accumulate(tokens, rec.get("tokens_in"))
            tokens = _accumulate(tokens, rec.get("tokens_out"))
            cost = _accumulate(cost, rec.get("cost"))
            wall = _accumulate(wall, rec.get("duration_s"))

    ext_path = root / ".rh" / "external-requests.jsonl"
    if ext_path.is_file():
        external: Number | str = sum(
            1 for ln in ext_path.read_text(encoding="utf-8").splitlines() if ln.strip()
        )
    else:
        external = UNKNOWN

    return {
        "model_calls": model_calls,
        "tokens": tokens,
        "cost": cost,
        "wall_time_s": wall,
        "external_requests": external,
    }


def _finding(check_id: str, severity: str, reason: str, **extra: Any) -> dict[str, Any]:
    out: dict[str, Any] = {
        "check_id": check_id,
        "severity": severity,
        "reason": reason,
        "location": {},
        "proposed_action": extra.pop("proposed_action", ""),
    }
    out.update(extra)
    return out


def _ratio(used: Number, limit: Number) -> float:
    if limit <= 0:
        return 1.0 if used > 0 else 0.0
    return used / limit


def evaluate(
    budget: dict[str, Any] | None,
    usage: dict[str, Number | str],
    *,
    thresholds: tuple[float, ...] | None = None,
) -> dict[str, Any]:
    """Compute per-limit ratios, the overall state, and threshold findings."""
    limits = (budget or {}).get("limits") or {}
    thr = tuple(thresholds or (budget or {}).get("thresholds") or DEFAULT_THRESHOLDS)
    warn = sorted(t for t in thr if t < 1.0)

    per_limit: dict[str, Any] = {}
    findings: list[dict[str, Any]] = []
    any_unknown = False
    any_exhausted = False

    for key in LIMIT_KEYS:
        if key not in limits:
            continue
        limit = limits[key]
        used = usage.get(key, UNKNOWN)
        if used == UNKNOWN:
            any_unknown = True
            per_limit[key] = {"limit": limit, "used": UNKNOWN, "ratio": UNKNOWN, "state": UNKNOWN}
            findings.append(
                _finding(
                    "budget.unknown_usage",
                    "major",
                    f"usage for {key!r} is unknown; the budget cannot be confirmed",
                    observed=key,
                    proposed_action="Record per-call telemetry, or rely on counts and wall time.",
                )
            )
            continue
        ratio = _ratio(float(used), float(limit))
        state = "ok"
        if ratio >= 1.0:
            any_exhausted = True
            state = "exhausted"
            findings.append(
                _finding(
                    "budget.exhausted",
                    "blocker",
                    f"{key}: {used} of {limit} ({ratio:.0%}) reaches the limit",
                    observed=used,
                    expected=limit,
                    proposed_action="Stop with partial artifacts; raise the limit to continue.",
                )
            )
        else:
            crossed = [t for t in warn if ratio >= t]
            if crossed:
                top = max(crossed)
                cid = "budget.threshold_80" if top >= 0.8 else "budget.threshold_50"
                state = f"at_{int(top * 100)}pct"
                findings.append(
                    _finding(
                        cid,
                        "info",
                        f"{key}: {used} of {limit} ({ratio:.0%}) crossed {int(top * 100)}%",
                        observed=used,
                        expected=limit,
                    )
                )
        per_limit[key] = {"limit": limit, "used": used, "ratio": round(ratio, 4), "state": state}

    if any_exhausted:
        overall = "exhausted"
    elif any_unknown:
        overall = UNKNOWN
    else:
        overall = "ok"

    return {"state": overall, "limits": per_limit, "findings": findings, "thresholds": list(thr)}


def check(
    budget: dict[str, Any] | None,
    usage: dict[str, Number | str],
    *,
    paid: bool = False,
    thresholds: tuple[float, ...] | None = None,
) -> dict[str, Any]:
    """The pre-call guard: evaluate limits and, for a paid call, the paid gate.

    ``allowed`` is false when any blocker is present (an exhausted limit, or a
    paid call that is not authorised). An ``unknown`` state is allowed but
    flagged ``major``.
    """
    result = evaluate(budget, usage, thresholds=thresholds)
    findings = list(result["findings"])
    if paid:
        enabled = (
            bool(budget)
            and budget.get("paid_calls") == "enabled"
            and bool(budget.get("enabled_by"))
        )
        if not enabled:
            findings.append(
                _finding(
                    "budget.paid_call_disabled",
                    "blocker",
                    "paid calls are disabled; enable them with a recorded approval (ADR-017)",
                    proposed_action="rh budget set --paid enabled --approval <AR-id>",
                )
            )
    allowed = not any(f["severity"] == "blocker" for f in findings)
    return {
        "allowed": allowed,
        "state": result["state"],
        "limits": result["limits"],
        "findings": findings,
        "paid": paid,
    }
