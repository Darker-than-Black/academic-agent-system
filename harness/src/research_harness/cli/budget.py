"""`rh budget show|set|check` (M3-01, models-budget.md, FR-13/NFR-05)."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

from research_harness.budget import controller
from research_harness.cli.context import object_root
from research_harness.core.envelope import build_envelope

_COMMAND = "budget"
_INT_LIMITS = {"model_calls", "tokens", "external_requests"}
_FLOAT_LIMITS = {"cost", "wall_time_s"}


def register(sub: argparse._SubParsersAction) -> None:
    bg = sub.add_parser(_COMMAND, help="Budget limits and the cost guard.")
    sa = bg.add_subparsers(dest="budget_action", metavar="action", required=True)

    sa.add_parser("show", help="Show limits, usage and state.")

    st = sa.add_parser("set", help="Set limits, scope or the paid-calls gate.")
    st.add_argument(
        "--limit",
        action="append",
        metavar="KEY=VALUE",
        help="Set a limit, e.g. tokens=100000 (repeatable). Keys: "
        + ", ".join(controller.LIMIT_KEYS),
    )
    st.add_argument("--scope", choices=("object", "task"))
    st.add_argument("--paid", choices=("enabled", "disabled"))
    st.add_argument("--approval", help="Approval id authorising paid calls (enabled_by).")

    ck = sa.add_parser("check", help="Guard: is a call allowed under the budget now?")
    ck.add_argument("--paid", action="store_true", help="Check the paid-calls gate too.")


def handles(command: str) -> bool:
    return command == _COMMAND


def route(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    if args.budget_action == "show":
        return _show(args, lang)
    if args.budget_action == "set":
        return _set(args, lang)
    return _check(args, lang)


def _status_for(state: str, findings: list[dict[str, Any]]) -> str:
    if any(f["severity"] == "blocker" for f in findings):
        return "blocked"
    return "partial" if state == controller.UNKNOWN else "ok"


def _show(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = object_root(args)
    budget = controller.load_budget(root)
    usage = controller.usage_from_calls(root)
    ev = controller.evaluate(budget, usage)
    status = _status_for(ev["state"], ev["findings"])
    data = {
        "configured": budget is not None,
        "budget": budget,
        "usage": usage,
        "state": ev["state"],
        "limits": ev["limits"],
    }
    return (
        build_envelope(
            command=_COMMAND,
            status=status,
            lang=lang,
            message_key="budget.shown",
            message_params={"state": ev["state"]},
            data=data,
            findings=ev["findings"],
        ),
        3 if status == "blocked" else 0,
    )


def _parse_limit(raw: str) -> tuple[str, int | float]:
    key, _, value = raw.partition("=")
    key = key.strip()
    if key not in controller.LIMIT_KEYS or not value:
        raise ValueError(raw)
    return key, (float(value) if key in _FLOAT_LIMITS else int(value))


def _set(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = object_root(args)
    budget = controller.load_budget(root) or {"scope": "object", "paid_calls": "disabled"}

    if args.scope:
        budget["scope"] = args.scope

    if args.limit:
        limits = dict(budget.get("limits") or {})
        for raw in args.limit:
            try:
                key, value = _parse_limit(raw)
            except ValueError:
                return (
                    build_envelope(
                        command=_COMMAND,
                        status="invalid",
                        lang=lang,
                        message_key="error.budget_bad_limit",
                        message_params={"arg": raw},
                        data={"arg": raw},
                    ),
                    2,
                )
            limits[key] = value
        budget["limits"] = limits

    if args.paid == "enabled":
        approval = args.approval or budget.get("enabled_by")
        if not approval:
            return (
                build_envelope(
                    command=_COMMAND,
                    status="blocked",
                    lang=lang,
                    message_key="error.budget_paid_needs_approval",
                    data={"paid_calls": "disabled"},
                ),
                3,
            )
        budget["paid_calls"] = "enabled"
        budget["enabled_by"] = approval
    elif args.paid == "disabled":
        budget["paid_calls"] = "disabled"
        budget.pop("enabled_by", None)

    _write_budget(controller.budget_path(root), budget)
    return (
        build_envelope(
            command=_COMMAND,
            status="ok",
            lang=lang,
            message_key="budget.set_done",
            message_params={"paid": budget["paid_calls"]},
            data={"budget": budget},
        ),
        0,
    )


def _write_budget(path: Path, budget: dict[str, Any]) -> None:
    path.write_text(yaml.safe_dump(budget, allow_unicode=True, sort_keys=True), encoding="utf-8")


def _check(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = object_root(args)
    budget = controller.load_budget(root)
    usage = controller.usage_from_calls(root)
    result = controller.check(budget, usage, paid=bool(args.paid))
    allowed = result["allowed"]
    status = _status_for(result["state"], result["findings"])
    return (
        build_envelope(
            command=_COMMAND,
            status=status,
            lang=lang,
            message_key="budget.check_ok" if allowed else "budget.check_blocked",
            message_params={"state": result["state"]},
            data={
                "allowed": allowed,
                "paid": result["paid"],
                "state": result["state"],
                "limits": result["limits"],
            },
            findings=result["findings"],
        ),
        0 if allowed else 3,
    )
