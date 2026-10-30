"""`rh gate request|explain|record|list` (M1-10)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from research_harness.cli.context import object_root
from research_harness.core.clock import default_clock
from research_harness.core.envelope import build_envelope
from research_harness.core.errors import InvalidInputError
from research_harness.core.hashing import file_hash
from research_harness.gates import briefing, interactive, records, requests
from research_harness.i18n import t
from research_harness.state import freshness

_COMMAND = "gate"
_EXTERNAL_ROLES = {
    "supervisor",
    "ethics_committee",
    "editorial_office",
    "department",
    "academic_council",
    "defense_council",
}


def register(sub: argparse._SubParsersAction) -> None:
    gt = sub.add_parser(_COMMAND, help="Gates and approvals.")
    sa = gt.add_subparsers(dest="gate_action", metavar="action", required=True)
    req = sa.add_parser("request", help="Open an approval request for a gate.")
    req.add_argument("gate")
    exp = sa.add_parser("explain", help="Print a gate briefing (read-only).")
    exp.add_argument("target", help="GATE id (G0..GE) or AR-NNNN request id.")
    rec = sa.add_parser("record", help="Record an approval (human terminal only).")
    rec.add_argument("gate")
    rec.add_argument("--decision")
    rec.add_argument("--reason")
    rec.add_argument("--conditions")
    rec.add_argument("--actor-role", dest="actor_role", default="author")
    rec.add_argument("--actor-label", dest="actor_label")
    rec.add_argument("--document")
    sa.add_parser("list", help="List requests and approvals with validity.")


def handles(command: str) -> bool:
    return command == _COMMAND


def route(args: Any, lang: str) -> tuple[dict[str, Any], int]:
    root = object_root(args)
    action = args.gate_action
    if action == "request":
        ar = requests.request_gate(root, args.gate, lang)
        return _ok(
            lang,
            "gate.requested",
            {"gate": args.gate, "ar": ar},
            {"request": ar, "briefing_path": f"approvals/requests/{ar}.md"},
        )
    if action == "explain":
        return _explain(root, args.target, lang)
    if action == "list":
        return _list(root, lang)
    return _record(root, args, lang)


def _ok(
    lang: str, key: str, params: dict[str, Any], data: dict[str, Any]
) -> tuple[dict[str, Any], int]:
    return build_envelope(
        command=_COMMAND, status="ok", lang=lang, message_key=key, message_params=params, data=data
    ), 0


def _explain(root: Path, target: str, lang: str) -> tuple[dict[str, Any], int]:
    if target.startswith("AR-"):
        rf = requests.requests_dir(root) / f"{target}.json"
        if not rf.is_file():
            raise InvalidInputError("error.gate_unknown")
        briefing_path = root / json.loads(rf.read_text(encoding="utf-8"))["briefing_path"]
        text = briefing_path.read_text(encoding="utf-8")
        gate = json.loads(rf.read_text(encoding="utf-8"))["gate"]
    else:
        gate = target
        text = briefing.render(root, gate, lang)
    return _ok(lang, "gate.explained", {"gate": gate}, {"briefing": text})


def _list(root: Path, lang: str) -> tuple[dict[str, Any], int]:
    cur = requests.open_requests(root)
    open_reqs = [{"id": r["id"], "gate": r["gate"], "status": r["status"]} for r in cur]
    approvals: list[dict[str, Any]] = []
    ap_file = records.approvals_path(root)
    if ap_file.is_file():
        graph = freshness.load_graph(root)
        for line in ap_file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            ap = json.loads(line)
            approvals.append(
                {
                    "id": ap["id"],
                    "gate": ap["gate"],
                    "decision": ap["decision"],
                    "valid": freshness.approval_valid(root, ap, graph),
                }
            )
    return _ok(
        lang,
        "gate.listed",
        {"requests": len(open_reqs), "approvals": len(approvals)},
        {"requests": open_reqs, "approvals": approvals},
    )


def _record(root: Path, args: Any, lang: str) -> tuple[dict[str, Any], int]:
    gate = args.gate
    role = args.actor_role
    external = role in _EXTERNAL_ROLES

    if external:
        return _record_external(root, args, lang, gate, role)

    # author / co_author
    if not interactive.is_human_channel():
        ar = requests.request_gate(root, gate, lang)
        briefing_path = f"approvals/requests/{ar}.md"
        command = f"rh --object {_oid(root)} gate record {gate}"
        return (
            build_envelope(
                command=_COMMAND,
                status="blocked",
                lang=lang,
                message_key="gate.record_blocked",
                message_params={"briefing": briefing_path},
                next_actions=[
                    {
                        "command": command,
                        "who": "author",
                        "why": t("gate.record_terminal", lang),
                        "briefing": briefing_path,
                    }
                ],
                data={"request": ar, "briefing_path": briefing_path},
            ),
            3,
        )

    req = requests.find_open_request(root, gate)
    prefill = {
        "decision": {"approved": "1", "rejected": "2", "approved_with_conditions": "3"}.get(
            args.decision
        ),
        "reason": args.reason,
        "conditions": args.conditions,
    }
    rec = interactive.run_record(
        root, gate, lang, prefill=prefill, request_id=req["id"] if req else None
    )
    if rec is None:
        return build_envelope(
            command=_COMMAND, status="blocked", lang=lang, message_key="gate.record_aborted"
        ), 3
    return _ok(
        lang,
        "gate.recorded",
        {"ap": rec["id"], "gate": gate, "decision": rec["decision"]},
        {"approval": rec},
    )


def _record_external(
    root: Path, args: Any, lang: str, gate: str, role: str
) -> tuple[dict[str, Any], int]:
    if not args.document:
        raise InvalidInputError("error.gate_document_required")
    if not args.decision:
        raise InvalidInputError("error.gate_decision_required")
    if not interactive.is_human_channel():
        ar = requests.request_gate(root, gate, lang)
        briefing_path = f"approvals/requests/{ar}.md"
        return (
            build_envelope(
                command=_COMMAND,
                status="blocked",
                lang=lang,
                message_key="gate.record_blocked",
                message_params={"briefing": briefing_path},
                next_actions=[
                    {
                        "command": (
                            f"rh --object {_oid(root)} gate record {gate} "
                            f"--actor-role {role} --document <path>"
                        ),
                        "who": "author",
                        "why": t("gate.record_terminal", lang),
                    }
                ],
                data={"request": ar},
            ),
            3,
        )
    doc_path = Path(args.document)
    document = {
        "path": doc_path.as_posix(),
        "sha256": file_hash(doc_path),
        "description": f"{gate} {role}",
        "date": default_clock().now_rfc3339(),
    }
    req = requests.find_open_request(root, gate)
    rec = records.record(
        root,
        gate,
        decision=args.decision,
        reason=args.reason or "",
        target=requests.current_target(root),
        actor_role=role,
        actor_label=args.actor_label or role,
        channel="external_document",
        conditions=args.conditions,
        document=document,
        request_id=req["id"] if req else None,
    )
    return _ok(
        lang,
        "gate.recorded",
        {"ap": rec["id"], "gate": gate, "decision": rec["decision"]},
        {"approval": rec},
    )


def _oid(root: Path) -> str:
    return json.loads((root / "object.json").read_text(encoding="utf-8"))["id"]
