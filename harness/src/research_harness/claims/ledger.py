"""Claim ledger: per-unit ``manuscript/<U>/claims.json`` plus the object index
``claims/ledger.jsonl`` rebuilt from units on every operation (claims-text.md).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_harness.claims import PRODUCER
from research_harness.claims.support import compute_support
from research_harness.core.clock import default_clock
from research_harness.core.hashing import text_hash
from research_harness.schemas import validate

_MATERIAL = ("critical", "material")


def unit_dir(root: Path, unit_id: str) -> Path:
    return root / "manuscript" / unit_id


def claims_file(root: Path, unit_id: str) -> Path:
    return unit_dir(root, unit_id) / "claims.json"


def ledger_path(root: Path) -> Path:
    return root / "claims" / "ledger.jsonl"


def load_unit_claims(root: Path, unit_id: str) -> list[dict[str, Any]]:
    path = claims_file(root, unit_id)
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("claims", [])


def _unit_ids(root: Path) -> list[str]:
    man = root / "manuscript"
    if not man.is_dir():
        return []
    return sorted(d.name for d in man.iterdir() if (d / "claims.json").is_file())


def _normalize(unit_id: str, claim: dict[str, Any], index: int) -> dict[str, Any]:
    c = dict(claim)
    c.setdefault("schema_version", "0.2")
    c.setdefault("id", f"C-{index}")
    c.setdefault("created_at", default_clock().now_rfc3339())
    c.setdefault("producer", PRODUCER)
    c.setdefault("inputs", [])
    c.setdefault("dependencies", [])
    c.setdefault("evidence", [])
    c.setdefault("support", "unreviewed")
    c["unit_id"] = unit_id
    loc = dict(c.get("location") or {})
    loc["unit_id"] = unit_id
    if "text_sha256" not in loc:
        loc["text_sha256"] = text_hash(c["text"].encode("utf-8"))
    c["location"] = loc
    return c


def set_claims(
    root: Path, unit_id: str, claims: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Validate and store a unit's claims; apply caps; rebuild the ledger."""
    findings: list[dict[str, Any]] = []
    stored: list[dict[str, Any]] = []
    for i, claim in enumerate(claims, start=1):
        c = _normalize(unit_id, claim, i)
        support, caps = compute_support(root, c)
        c["support"] = support
        findings.extend(caps)
        errors = validate("claim", c)
        if errors:
            raise ValueError(f"invalid claim {c['id']}: {errors}")
        stored.append(c)

    unit_dir(root, unit_id).mkdir(parents=True, exist_ok=True)
    claims_file(root, unit_id).write_text(
        json.dumps(
            {"schema_version": "0.2", "unit_id": unit_id, "claims": stored},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    rebuild_ledger(root)
    return stored, findings


def rebuild_ledger(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for uid in _unit_ids(root):
        for c in load_unit_claims(root, uid):
            rows.append(
                {
                    "id": c["id"],
                    "unit_id": uid,
                    "kind": c["kind"],
                    "materiality": c["materiality"],
                    "support": c["support"],
                }
            )
    path = ledger_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8"
    )
    return rows


def check_claims(
    root: Path, unit_id: str | None = None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Recompute caps for stored claims; return (findings, claims)."""
    findings: list[dict[str, Any]] = []
    claims: list[dict[str, Any]] = []
    uids = [unit_id] if unit_id else _unit_ids(root)
    for uid in uids:
        for c in load_unit_claims(root, uid):
            support, caps = compute_support(root, c)
            if support != c["support"]:
                caps.append(
                    {
                        "check_id": "claims.support_stale",
                        "severity": "major",
                        "reason": (
                            f"{c['id']}: stored support {c['support']!r} != recomputed {support!r}"
                        ),
                        "location": {"ref": f"claim:{c['id']}"},
                        "proposed_action": "",
                    }
                )
            findings.extend(caps)
            claims.append(c)
    return findings, claims


def coverage(root: Path) -> dict[str, Any]:
    """Coverage with an explicit denominator = all material claims (FR-09)."""
    rows = rebuild_ledger(root)
    material = [r for r in rows if r["materiality"] in _MATERIAL]
    by_support: dict[str, int] = {}
    for r in material:
        by_support[r["support"]] = by_support.get(r["support"], 0) + 1
    return {
        "denominator": len(material),
        "material_claims": len(material),
        "total_claims": len(rows),
        "by_support": by_support,
    }
