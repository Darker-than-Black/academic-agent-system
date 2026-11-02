"""Dataset registry (M3-18, FR-57). A dataset enters an analysis only with
recorded terms of use (invariant 1); no terms → it is not admitted, and a run
that uses it is a blocker (``analysis.dataset_terms_missing``). Downloads happen
only here, never during a run (invariant 2); this module copies from a local
path and records a hash, and leaves network fetching to the author.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from research_harness.core.clock import default_clock
from research_harness.core.hashing import file_hash
from research_harness.schemas import validate

_HUMAN = {"kind": "human", "name": "author", "version": "0.1.0"}
UNKNOWN = "unknown"


def registry_path(root: Path) -> Path:
    return root / "analysis" / "datasets" / "registry.json"


def data_dir(root: Path) -> Path:
    return root / "analysis" / "data"


def load(root: Path) -> list[dict[str, Any]]:
    path = registry_path(root)
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("datasets", [])


def _save(root: Path, datasets: list[dict[str, Any]]) -> None:
    path = registry_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"schema_version": "0.2", "datasets": datasets}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )


def _next_id(datasets: list[dict[str, Any]]) -> str:
    nums = [int(d["id"].split("-")[1]) for d in datasets if d.get("id", "").startswith("D-")]
    return f"D-{max(nums, default=0) + 1:03d}"


def _terms(terms: str | None, root: Path) -> dict[str, str]:
    """Record terms from a local file (hashed reference) or a URL/text. Absent
    terms are recorded as ``unknown`` so the admission check blocks them (H7)."""
    if not terms:
        return {"text_or_url": UNKNOWN, "verified_at": UNKNOWN}
    candidate = root / terms if (root / terms).is_file() else Path(terms)
    if candidate.is_file():
        return {"text_or_url": str(terms), "verified_at": default_clock().now_rfc3339()}
    return {"text_or_url": terms, "verified_at": default_clock().now_rfc3339()}


def add(
    root: Path,
    *,
    name: str,
    version: str,
    url: str | None = None,
    terms: str | None = None,
    from_path: str | None = None,
    no_copy: bool = False,
    synthetic: bool = False,
) -> dict[str, Any]:
    """Register a dataset. With ``from_path`` and not ``no_copy`` the file is
    copied into ``analysis/data/`` and hashed; otherwise the hash is ``unknown``."""
    datasets = load(root)
    ds_id = _next_id(datasets)
    storage = "no_copy" if no_copy else "copy"
    sha = UNKNOWN

    if from_path and not no_copy:
        src = root / from_path if (root / from_path).is_file() else Path(from_path)
        if src.is_file():
            dest = data_dir(root) / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)
            sha = file_hash(dest)

    record: dict[str, Any] = {
        "schema_version": "0.2",
        "id": ds_id,
        "created_at": default_clock().now_rfc3339(),
        "producer": _HUMAN,
        "name": name,
        "version": version,
        "terms": _terms(terms, root),
        "sha256": sha,
        "storage": storage,
        "synthetic": bool(synthetic),
    }
    if url:
        record["url"] = url
    errors = validate("dataset", record)
    if errors:
        raise ValueError(f"invalid dataset record: {errors}")
    datasets.append(record)
    _save(root, datasets)
    return record


def admitted(dataset: dict[str, Any]) -> bool:
    """A dataset is admitted only with real terms of use (invariant 1)."""
    terms = dataset.get("terms", {})
    return terms.get("text_or_url", UNKNOWN) != UNKNOWN and terms.get("verified_at") != UNKNOWN


def terms_findings(root: Path, dataset_ids: list[str] | None = None) -> list[dict[str, Any]]:
    """``analysis.dataset_terms_missing`` blocker for each dataset without terms."""
    by_id = {d["id"]: d for d in load(root)}
    ids = dataset_ids if dataset_ids is not None else list(by_id)
    findings: list[dict[str, Any]] = []
    for ds_id in ids:
        ds = by_id.get(ds_id)
        if ds is None or not admitted(ds):
            findings.append(
                {
                    "check_id": "analysis.dataset_terms_missing",
                    "severity": "blocker",
                    "reason": f"dataset {ds_id} has no recorded terms of use; not admitted",
                    "location": {"dataset": ds_id},
                    "observed": (ds or {}).get("terms"),
                    "proposed_action": "Record the dataset's terms (rh dataset add --terms).",
                }
            )
    return findings
