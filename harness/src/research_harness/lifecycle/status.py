"""Build the status report (03 §3) and render it as text (02-lifecycle §8.2)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_harness.gates import requests
from research_harness.i18n import t
from research_harness.intake import answers as intake_answers
from research_harness.lifecycle import stages as stage_model
from research_harness.state import dirty, freshness, recovery


def _object(root: Path) -> dict[str, Any]:
    return json.loads((root / "object.json").read_text(encoding="utf-8"))


def _current_stage(states: dict[str, Any], ids: list[str]) -> str:
    for sid in ids:
        if states.get(sid, {}).get("state") == "active":
            return sid
    for sid in ids:
        st = states.get(sid, {}).get("state")
        if st in ("blocked", "failed", "stale"):
            return sid
    for sid in ids:
        if states.get(sid, {}).get("state", "pending") == "pending":
            return sid
    return ids[-1]


def _gates(root: Path, kind: str) -> list[dict[str, Any]]:
    out = []
    graph = freshness.load_graph(root)
    ap_file = root / "approvals" / "approvals.jsonl"
    approvals = []
    if ap_file.is_file():
        approvals = [
            json.loads(line)
            for line in ap_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    for gate in stage_model.gates_for(kind):
        valid: Any = False
        for ap in approvals:
            if ap["gate"] == gate and freshness.approval_valid(root, ap, graph):
                valid = True
                break
        out.append(
            {
                "gate": gate,
                "required": True,
                "request_open": bool(requests.open_requests(root, gate)),
                "approval_valid": valid,
            }
        )
    return out


def _unknowns(root: Path) -> list[dict[str, Any]]:
    data = intake_answers.load(root)
    return list(data.get("consequences", []))


def _blockers(root: Path, obj: Any, gates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    missing = intake_answers.missing_core(root)
    if missing:
        blockers.append({"stage": "A0", "reason": "intake.required_missing", "questions": missing})
    for g in gates:
        if g["gate"] == "G0" and not g["approval_valid"]:
            blockers.append({"gate": "G0", "reason": "gate.g0_not_approved"})
    return blockers


def _next_action(
    root: Path, obj: Any, gates: list[dict[str, Any]], missing: list[str], lang: str
) -> dict[str, Any]:
    oid = obj["id"]
    if missing:
        return {
            "command": f"rh --object {oid} intake questions",
            "who": "agent",
            "why": t("status.why_intake", lang),
        }
    g0 = next((g for g in gates if g["gate"] == "G0"), None)
    if g0 and not g0["approval_valid"]:
        if g0["request_open"]:
            return {
                "command": f"rh --object {oid} gate record G0",
                "who": "author",
                "why": t("status.why_g0_record", lang),
            }
        return {
            "command": f"rh --object {oid} gate request G0",
            "who": "agent",
            "why": t("status.why_g0_request", lang),
        }
    return {
        "command": f"rh --object {oid} status",
        "who": "agent",
        "why": t("status.proceed", lang),
    }


def build_report(root: Path, lang: str = "uk") -> dict[str, Any]:
    obj = _object(root)
    kind = obj["kind"]
    ids = stage_model.stage_ids(kind)
    states_raw = obj.get("stages") or {}
    states = {sid: states_raw.get(sid, {}).get("state", "pending") for sid in ids}

    gates = _gates(root, kind)
    missing = intake_answers.missing_core(root)
    rec = recovery.recover(root, repair=False)

    return {
        "object": {
            "id": obj["id"],
            "kind": kind,
            "title": obj.get("title", obj["id"]),
            "folder": root.name,
            "mode": obj.get("operation_mode", "create"),
            "document_kind": obj.get("document_kind", "unknown"),
            "study_kind": obj.get("study_kind", "unknown"),
            "languages": obj.get("languages", {}),
            "autonomy": obj.get("autonomy", "gates"),
        },
        "stage": {"current": _current_stage(states_raw, ids), "states": states},
        "gates": gates,
        "blockers": _blockers(root, obj, gates),
        "unknowns": _unknowns(root),
        "dirty": sorted(dirty.dirty_set(root)),
        "stale": _stale(root),
        "locks_and_recovery": _locks(root, rec),
        "next_action": _next_action(root, obj, gates, missing, lang),
    }


def _stale(root: Path) -> dict[str, Any]:
    rep = freshness.freshness_report(root)
    return {"count": rep["stale_count"], "examples": rep["stale"][:5]}


def _locks(root: Path, rec: list[dict[str, Any]]) -> dict[str, Any]:
    lock = root / ".rh" / "lock"
    quarantine = root / ".rh" / "quarantine"
    quarantined = [p.name for p in quarantine.iterdir()] if quarantine.is_dir() else []
    return {
        "lock_held": lock.is_file(),
        "quarantined": quarantined,
        "recovery_findings": rec,
    }


def render_text(report: dict[str, Any], lang: str) -> str:
    o = report["object"]
    lines = [f"{o['id']} — {o['title']} [{o['kind']}]"]
    cur = report["stage"]["current"]
    lines.append(f"  stage: {cur} ({report['stage']['states'].get(cur)})")
    for g in report["gates"]:
        lines.append(
            f"  gate {g['gate']}: request_open={g['request_open']} valid={g['approval_valid']}"
        )
    if report["blockers"]:
        lines.append(f"  blockers: {len(report['blockers'])}")
    if report["unknowns"]:
        lines.append(f"  unknowns: {len(report['unknowns'])}")
    if report["dirty"]:
        lines.append(f"  dirty: {len(report['dirty'])}")
    lines.append(f"  stale: {report['stale']['count']}")
    na = report["next_action"]
    lines.append(f"  → {na['who']}: {na['command']}")
    return "\n".join(lines) + "\n"
