"""Figures built from result rows (M3-20, analysis-sandbox.md, FR-18).

A figure is defined by the rows it draws and the script that draws them; the
harness hands the script those rows, rebuilds the image with the network off,
and records the row content hashes. A figure is stale the moment any row it uses
changes or disappears (invariant 3) — reported as ``analysis.figure_stale``.
Plots come only from rows (the author's script does the plotting; this core
stays LLM- and dependency-free)."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from research_harness.analysis import rows as rows_mod
from research_harness.analysis import sandbox
from research_harness.core.clock import default_clock
from research_harness.core.errors import BlockedError
from research_harness.core.hashing import canonical_json_hash, file_hash
from research_harness.schemas import validate

_AGENT = {"kind": "model", "name": "analysis", "version": "0.1.0"}


def figures_dir(root: Path) -> Path:
    return root / "assets" / "figures"


def definition_path(root: Path, fig_id: str) -> Path:
    return figures_dir(root) / f"{fig_id}.json"


def load(root: Path, fig_id: str) -> dict[str, Any] | None:
    path = definition_path(root, fig_id)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_ids(root: Path) -> list[str]:
    d = figures_dir(root)
    return sorted(p.stem for p in d.glob("FIG-*.json")) if d.is_dir() else []


def _next_id(root: Path) -> str:
    nums = [int(fid.split("-")[1]) for fid in list_ids(root)]
    return f"FIG-{max(nums, default=0) + 1:03d}"


def _row_hashes(root: Path, row_ids: list[str]) -> tuple[list[str], list[str]]:
    """(sorted content hashes of the referenced rows, ids of missing rows)."""
    by_id = rows_mod.by_id(root)
    hashes: list[str] = []
    missing: list[str] = []
    for rid in row_ids:
        row = by_id.get(rid)
        if row is None:
            missing.append(rid)
        else:
            hashes.append(canonical_json_hash(row))
    return sorted(hashes), missing


def add(root: Path, *, script: str, row_ids: list[str], fmt: str = "svg") -> dict[str, Any]:
    """Register a figure definition (rows + plotting script); not built yet."""
    script_path = root / script if (root / script).is_file() else Path(script)
    if not script_path.is_file():
        raise BlockedError("error.figure_script_missing", params={"path": str(script)})
    fig_id = _next_id(root)
    record = {
        "schema_version": "0.2",
        "id": fig_id,
        "created_at": default_clock().now_rfc3339(),
        "producer": _AGENT,
        "rows": list(row_ids),
        "script": {"path": str(script), "sha256": file_hash(script_path)},
        "data_sha256": [],
        "format": fmt,
        "built_at": None,
    }
    _save(root, record)
    return record


def _save(root: Path, record: dict[str, Any]) -> None:
    errors = validate("figure", record)
    if errors:
        raise ValueError(f"invalid figure record: {errors}")
    figures_dir(root).mkdir(parents=True, exist_ok=True)
    definition_path(root, record["id"]).write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def build(root: Path, fig_id: str) -> dict[str, Any]:
    """Rebuild the figure from its rows and script, network off."""
    record = load(root, fig_id)
    if record is None:
        raise BlockedError("error.figure_unknown", params={"id": fig_id})
    hashes, missing = _row_hashes(root, record["rows"])
    if missing:
        raise BlockedError("error.figure_rows_missing", params={"ids": ", ".join(missing)})

    script_path = (
        root / record["script"]["path"]
        if (root / record["script"]["path"]).is_file()
        else Path(record["script"]["path"])
    )
    work = figures_dir(root) / f".build-{fig_id}"
    (work / "outputs").mkdir(parents=True, exist_ok=True)
    by_id = rows_mod.by_id(root)
    (work / "rows.json").write_text(
        json.dumps([by_id[r] for r in record["rows"]], ensure_ascii=False), encoding="utf-8"
    )

    caps = sandbox.capabilities()
    sandbox.write_guard(work)
    argv = [sys.executable, str(script_path.resolve())]
    if caps.namespace:
        argv = ["unshare", "-n", *argv]
    proc = subprocess.run(  # noqa: S603
        argv,
        cwd=work,
        env={"PYTHONPATH": str(work), "PATH": "/usr/bin:/bin:/usr/local/bin"},
        capture_output=True,
        text=True,
        timeout=sandbox.DEFAULT_TIMEOUT_S,
    )
    produced = work / "outputs" / f"figure.{record['format']}"
    if proc.returncode != 0 or not produced.is_file():
        shutil.rmtree(work, ignore_errors=True)
        raise BlockedError("error.figure_build_failed", params={"id": fig_id})

    image = figures_dir(root) / f"{fig_id}.{record['format']}"
    shutil.copyfile(produced, image)
    shutil.rmtree(work, ignore_errors=True)

    record["script"]["sha256"] = file_hash(script_path)  # the script as built from
    record["data_sha256"] = hashes
    record["built_at"] = default_clock().now_rfc3339()
    record["image_sha256"] = file_hash(image)
    _save(root, record)
    return record


def _script_changed(root: Path, record: dict[str, Any]) -> bool:
    script_path = (
        root / record["script"]["path"]
        if (root / record["script"]["path"]).is_file()
        else Path(record["script"]["path"])
    )
    if not script_path.is_file():
        return True
    return file_hash(script_path) != record["script"]["sha256"]


def is_stale(root: Path, fig_id: str) -> bool:
    record = load(root, fig_id)
    if record is None or not record.get("built_at"):
        return True
    image = figures_dir(root) / f"{fig_id}.{record['format']}"
    if not image.is_file():
        return True
    if _script_changed(root, record):
        return True
    hashes, missing = _row_hashes(root, record["rows"])
    return bool(missing) or hashes != record.get("data_sha256", [])


def stale_findings(root: Path) -> list[dict[str, Any]]:
    """``analysis.figure_stale`` (major, FR-18) for each figure out of date."""
    findings: list[dict[str, Any]] = []
    for fig_id in list_ids(root):
        if is_stale(root, fig_id):
            findings.append(
                {
                    "check_id": "analysis.figure_stale",
                    "severity": "major",
                    "reason": f"figure {fig_id} is stale: rebuild it from current rows",
                    "location": {"figure": fig_id},
                    "observed": fig_id,
                    "proposed_action": "Rebuild the figure (rh figure build FIG-ID).",
                }
            )
    return findings
