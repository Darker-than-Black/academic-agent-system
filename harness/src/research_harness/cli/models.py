"""`rh model resolve|downgrade|log` (M1-12, 03 §2.6)."""

from __future__ import annotations

import argparse
from typing import Any

from research_harness.cli.context import object_root
from research_harness.core.envelope import build_envelope
from research_harness.models import calls, config

_COMMAND = "model"


def register(sub: argparse._SubParsersAction) -> None:
    mt = sub.add_parser(_COMMAND, help="Model tiers and the call log.")
    sa = mt.add_subparsers(dest="model_action", metavar="action", required=True)
    rs = sa.add_parser("resolve", help="Resolve a role to a model for the host.")
    rs.add_argument("--role", required=True)
    rs.add_argument("--host")
    dg = sa.add_parser("downgrade", help="Record a pending downgrade for a role.")
    dg.add_argument("--role", required=True)
    dg.add_argument("--to", dest="to_tier", required=True)
    dg.add_argument("--reason", required=True)
    lg = sa.add_parser("log", help="Append a model call record.")
    lg.add_argument("--role", required=True)
    lg.add_argument("--model", required=True)
    lg.add_argument("--host")
    lg.add_argument("--tokens-in", dest="tokens_in", type=int)
    lg.add_argument("--tokens-out", dest="tokens_out", type=int)
    lg.add_argument("--cost", type=float)
    lg.add_argument("--status", choices=["ok", "failed"], default="ok")
    lg.add_argument("--purpose")


def handles(command: str) -> bool:
    return command == _COMMAND


def route(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    if args.model_action == "resolve":
        return _resolve(args, lang)
    if args.model_action == "downgrade":
        return _downgrade(args, lang)
    return _log(args, lang)


def _resolve(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    host = config.host_from_env(args.host)
    tier, model_id = config.resolve(args.role, host)
    if model_id is None and tier != "none":
        return (
            build_envelope(
                command=_COMMAND,
                status="blocked",
                lang=lang,
                message_key="model.unknown_tier",
                message_params={"role": args.role, "host": host, "tier": tier},
                data={"role": args.role, "host": host, "tier": tier, "model": None},
            ),
            3,
        )
    return (
        build_envelope(
            command=_COMMAND,
            status="ok",
            lang=lang,
            message_key="model.resolved",
            message_params={"role": args.role, "model": model_id or "none"},
            data={"role": args.role, "host": host, "tier": tier, "model": model_id},
        ),
        0,
    )


def _downgrade(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = object_root(args)
    from_tier = config.tier_for_role(args.role)
    entry = calls.record_downgrade(
        root, args.role, from_tier=from_tier, to_tier=args.to_tier, reason=args.reason
    )
    return (
        build_envelope(
            command=_COMMAND,
            status="ok",
            lang=lang,
            message_key="model.downgraded",
            message_params={"role": args.role, "to": args.to_tier},
            data={"role": args.role, "downgrade": entry},
        ),
        0,
    )


def _log(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = object_root(args)
    host = config.host_from_env(args.host)
    tier = config.tier_for_role(args.role)
    rec = calls.log_call(
        root,
        host=host,
        role=args.role,
        tier_required=tier,
        model_id=args.model,
        purpose=args.purpose or calls.UNKNOWN,
        tokens_in=args.tokens_in if args.tokens_in is not None else calls.UNKNOWN,
        tokens_out=args.tokens_out if args.tokens_out is not None else calls.UNKNOWN,
        cost=args.cost if args.cost is not None else calls.UNKNOWN,
        status=args.status,
    )
    return (
        build_envelope(
            command=_COMMAND,
            status="ok",
            lang=lang,
            message_key="model.logged",
            message_params={"id": rec["id"]},
            data={"call": rec},
        ),
        0,
    )
