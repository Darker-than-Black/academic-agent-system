"""Asset registry and rights check (integrity.md; M3-12, FR-17).

Each figure/table/image carries its origin and rights. A ``third_party`` asset
without ``licensed`` or ``permission_documented`` rights blocks a verified
export (``integrity.asset_rights``). Deterministic; no LLM.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_harness.core.errors import InvalidInputError
from research_harness.core.hashing import compute_sha256
from research_harness.schemas import validate
from research_harness.state.snapshot import atomic_write_bytes

OK_RIGHTS = {"licensed", "permission_documented"}


def registry_path(root: Path) -> Path:
    return root / "assets" / "registry.json"


def load(root: Path) -> list[dict[str, Any]]:
    p = registry_path(root)
    if not p.is_file():
        return []
    data = json.loads(p.read_text(encoding="utf-8"))
    return data.get("assets", []) if isinstance(data, dict) else list(data)


def _next_id(assets: list[dict[str, Any]]) -> str:
    nums = [int(a["id"].split("-")[1]) for a in assets if a.get("id", "").startswith("AS-")]
    return f"AS-{max(nums, default=0) + 1:03d}"


def _write(root: Path, assets: list[dict[str, Any]]) -> None:
    body = json.dumps({"schema_version": "0.2", "assets": assets}, ensure_ascii=False, indent=2)
    atomic_write_bytes(registry_path(root), (body + "\n").encode("utf-8"))


def add_asset(
    root: Path,
    rel_path: str,
    *,
    origin: str,
    rights_status: str,
    kind: str = "other",
    license: str | None = None,
    source_ref: str | None = None,
    permission_doc_path: str | None = None,
    generated_from_rows: list[str] | None = None,
) -> dict[str, Any]:
    """Register one asset; computes the file hash and validates the record."""
    target = root / rel_path
    if not target.is_file():
        raise InvalidInputError("error.asset_file_missing")
    assets = load(root)
    rec: dict[str, Any] = {
        "id": _next_id(assets),
        "path": rel_path,
        "sha256": compute_sha256(target),
        "kind": kind,
        "origin": origin,
        "rights_status": rights_status,
    }
    if license:
        rec["license"] = license
    if source_ref:
        rec["source_ref"] = source_ref
    if generated_from_rows:
        rec["generated_from_rows"] = generated_from_rows
    if permission_doc_path:
        doc = root / permission_doc_path
        if not doc.is_file():
            raise InvalidInputError("error.asset_file_missing")
        rec["permission_doc"] = {"path": permission_doc_path, "sha256": compute_sha256(doc)}
    errors = validate("asset", rec)
    if errors:
        raise InvalidInputError("error.asset_invalid")
    assets.append(rec)
    _write(root, assets)
    return rec


def rights_findings(root: Path) -> list[dict[str, Any]]:
    """``integrity.asset_rights`` blocker for each third-party asset without rights."""
    findings: list[dict[str, Any]] = []
    for a in load(root):
        if a.get("origin") == "third_party" and a.get("rights_status") not in OK_RIGHTS:
            findings.append(
                {
                    "check_id": "integrity.asset_rights",
                    "severity": "blocker",
                    "reason": f"third-party asset {a['id']} has rights_status "
                    f"{a.get('rights_status')!r} (needs licensed or permission_documented)",
                    "location": {"path": a.get("path"), "asset": a["id"]},
                    "observed": a.get("rights_status"),
                    "proposed_action": "Document a licence or permission, or replace the asset.",
                }
            )
    return findings
