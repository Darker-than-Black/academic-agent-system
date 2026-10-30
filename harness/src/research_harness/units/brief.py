"""Unit briefs (``manuscript/<U>/brief.md``, YAML front matter + free text).

A unit is written only from its brief. Contribution points mark places where the
author's own view is needed; an unanswered point becomes a visible placeholder
``[[AUTHOR: <question>]]`` in the manuscript language, never an invented
position (FR-45, T49).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from research_harness.claims.ledger import rebuild_ledger
from research_harness.evidence.excerpts import load_excerpts
from research_harness.evidence.premises import load_premises
from research_harness.lab.matrix import load_rows
from research_harness.schemas import validate
from research_harness.sources import registry

_FRONT = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)
_TOKEN = re.compile(r"\{\{AP:([^}]+)\}\}")


def brief_path(root: Path, unit_id: str) -> Path:
    return root / "manuscript" / unit_id / "brief.md"


def save_brief(root: Path, unit_id: str, brief: dict[str, Any], body: str = "") -> dict[str, Any]:
    brief = dict(brief)
    brief.setdefault("schema_version", "0.2")
    brief["unit_id"] = unit_id
    errors = validate("brief", brief)
    if errors:
        raise ValueError(f"invalid brief: {errors}")
    path = brief_path(root, unit_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    front = yaml.safe_dump(brief, allow_unicode=True, sort_keys=False)
    path.write_text(f"---\n{front}---\n{body}", encoding="utf-8")
    return brief


def load_brief(root: Path, unit_id: str) -> tuple[dict[str, Any], str]:
    path = brief_path(root, unit_id)
    if not path.is_file():
        return {}, ""
    m = _FRONT.match(path.read_text(encoding="utf-8"))
    if not m:
        return {}, ""
    return yaml.safe_load(m.group(1)) or {}, m.group(2)


def _resolvable_refs(root: Path) -> set[str]:
    refs: set[str] = set()
    for r in load_rows(root):
        refs.add(f"matrix:{r['id']}")
    for e in load_excerpts(root):
        refs.add(f"excerpt:{e['id']}")
    for s in registry.load(root):
        refs.add(f"source:{s['id']}")
    for p in load_premises(root):
        refs.add(f"premise:{p['id']}")
    for c in rebuild_ledger(root):
        refs.add(f"claim:{c['id']}")
    return refs


# Ref kinds this check can resolve; others (e.g. finding:) are accepted as-is.
_CHECKED_KINDS = ("matrix", "excerpt", "source", "premise", "claim")


def check_brief(root: Path, unit_id: str) -> list[dict[str, Any]]:
    brief, _body = load_brief(root, unit_id)
    findings: list[dict[str, Any]] = []
    if not brief:
        return [
            {
                "check_id": "brief.required_missing",
                "severity": "blocker",
                "reason": f"{unit_id}: no brief",
                "location": {},
                "proposed_action": "",
            }
        ]
    if not brief.get("goal"):
        findings.append(_f("brief.required_missing", "blocker", f"{unit_id}: goal is required"))
    if not brief.get("target_volume"):
        findings.append(
            _f("brief.required_missing", "major", f"{unit_id}: target volume is required (FR-50)")
        )

    known = _resolvable_refs(root)
    for ref in brief.get("evidence_refs", []):
        kind = ref.split(":", 1)[0]
        if kind in _CHECKED_KINDS and ref not in known:
            findings.append(
                _f(
                    "brief.unknown_ref",
                    "major",
                    f"{unit_id}: evidence ref {ref!r} does not resolve",
                )
            )

    for point in unanswered_points(brief):
        findings.append(
            _f(
                "brief.point_unanswered",
                "info",
                f"{unit_id}: contribution point {point['id']!r} unanswered "
                "(a placeholder will be used)",
            )
        )
    return findings


def answer_point(root: Path, unit_id: str, point_id: str, answer: str) -> dict[str, Any]:
    brief, body = load_brief(root, unit_id)
    for point in brief.get("author_points", []):
        if point["id"] == point_id:
            point["answer"] = answer
            point["answered_by"] = "author"
    return save_brief(root, unit_id, brief, body)


def unanswered_points(brief: dict[str, Any]) -> list[dict[str, Any]]:
    return [p for p in brief.get("author_points", []) if not p.get("answer")]


def placeholder_for(point: dict[str, Any]) -> str:
    """The visible placeholder in the manuscript language (FR-45)."""
    return f"[[AUTHOR: {point['question']}]]"


def placeholders(brief: dict[str, Any]) -> list[str]:
    return [placeholder_for(p) for p in unanswered_points(brief)]


def render_points(brief: dict[str, Any], body: str) -> str:
    """Replace each ``{{AP:<id>}}`` token with the answer or a placeholder."""
    points = {p["id"]: p for p in brief.get("author_points", [])}

    def _sub(match: re.Match[str]) -> str:
        point = points.get(match.group(1))
        if point is None:
            return match.group(0)
        return point["answer"] if point.get("answer") else placeholder_for(point)

    return _TOKEN.sub(_sub, body)


def _f(check_id: str, severity: str, reason: str) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "severity": severity,
        "reason": reason,
        "location": {},
        "proposed_action": "",
    }
