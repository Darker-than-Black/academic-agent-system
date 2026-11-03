"""Run an analysis script in the sandbox (M3-19, FR-39/NFR-08).

argv only (no shell); cwd ``runs/<R>/work``; the network is off — a namespace
when available, otherwise the injected ``sitecustomize`` guard. A timeout or a
non-zero exit is ``failed`` (never shown as succeeded, invariant 4). The script's
``outputs/rows.json`` becomes validated result rows; run outputs are immutable
and a re-run gets a new id (invariant 5)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from research_harness.analysis import datasets as ds_mod
from research_harness.analysis import project, rows, sandbox
from research_harness.core.clock import default_clock
from research_harness.core.hashing import file_hash
from research_harness.schemas import validate

_AGENT = {"kind": "model", "name": "analysis", "version": "0.1.0"}
UNKNOWN = "unknown"


def runs_dir(root: Path) -> Path:
    return root / "runs"


def _next_run_id(root: Path) -> str:
    d = runs_dir(root)
    nums = [int(p.name.split("-")[1]) for p in d.glob("R-*")] if d.is_dir() else []
    return f"R-{max(nums, default=0) + 1:04d}"


def _interpreter(root: Path) -> tuple[str, str]:
    """Pick the interpreter for an analysis run.

    Prefer the per-object analysis venv (``analysis/.venv/bin/python``) so the
    script runs against the project's pinned scientific stack (numpy/pandas/…),
    which is the point of ``rh analysis init``. Fall back to the harness
    interpreter only when that venv has not been synced yet. Returns
    ``(python_path, source)`` where source is ``"analysis-venv"`` or ``"harness"``.
    """
    venv_py = project.project_dir(root) / ".venv" / "bin" / "python"
    if venv_py.is_file():
        return str(venv_py), "analysis-venv"
    return sys.executable, "harness"


def _lockfile_sha(root: Path) -> str:
    lock = project.project_dir(root) / "uv.lock"
    return file_hash(lock) if lock.is_file() else UNKNOWN


def _data_fingerprints(root: Path, dataset_ids: list[str]) -> tuple[list[dict], list[str]]:
    by_id = {d["id"]: d for d in ds_mod.load(root)}
    data: list[dict[str, Any]] = []
    missing: list[str] = []
    for did in dataset_ids:
        sha = by_id.get(did, {}).get("sha256", UNKNOWN)
        if sha == UNKNOWN:
            missing.append(f"dataset:{did}")
        else:
            data.append({"dataset_id": did, "sha256": sha})
    return data, missing


def run(
    root: Path,
    script: str | Path,
    *,
    dataset_ids: list[str] | None = None,
    seed: int | None = None,
    purpose: str = "analysis",
    timeout_s: int = sandbox.DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    script_path = Path(script)
    if not script_path.is_file():
        script_path = root / script
    if not script_path.is_file():
        from research_harness.core.errors import BlockedError

        raise BlockedError("error.analysis_script_missing", params={"path": str(script)})

    dataset_ids = dataset_ids or []
    clock = default_clock()
    run_id = _next_run_id(root)
    run_dir = runs_dir(root) / run_id
    work = run_dir / "work"
    (work / "outputs").mkdir(parents=True, exist_ok=True)

    caps = sandbox.capabilities()
    sandbox.write_guard(run_dir)  # sitecustomize for guard_only (harmless otherwise)
    env = {
        "PYTHONPATH": str(run_dir),
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "RH_ANALYSIS_SEED": str(seed) if seed is not None else "",
    }
    # No -I/-E/-s: the sitecustomize network guard is injected via PYTHONPATH and
    # must load at startup (guard_only). The script is the author's own analysis
    # code under analysis/scripts, not an untrusted download.
    interpreter, interp_source = _interpreter(root)
    argv = [interpreter, str(script_path.resolve())]
    if caps.namespace:
        argv = ["unshare", "-n", *argv]

    started = clock.now_rfc3339()
    status = "succeeded"
    exit_code: int | None = None
    try:
        proc = subprocess.run(  # noqa: S603
            argv,
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        exit_code = proc.returncode
        stdout, stderr = proc.stdout, proc.stderr
        if exit_code != 0:
            status = "failed"
    except subprocess.TimeoutExpired as exc:
        status = "failed"
        stdout = exc.stdout or ""
        stderr = (exc.stderr or "") + "\n[rh] timeout exceeded"
    (run_dir / "stdout.txt").write_text(stdout, encoding="utf-8")
    (run_dir / "stderr.txt").write_text(stderr, encoding="utf-8")
    finished = clock.now_rfc3339()

    data_fps, missing = _data_fingerprints(root, dataset_ids)
    lockfile_sha = _lockfile_sha(root)
    if lockfile_sha == UNKNOWN:
        missing.append("lockfile")

    origin = "simulated" if purpose == "instrument_pilot" else "executed"
    record: dict[str, Any] = {
        "schema_version": "0.2",
        "id": run_id,
        "created_at": started,
        "producer": _AGENT,
        "origin": origin,
        "status": status,
        "purpose": purpose,
        "network": "disabled",
        "sandbox": {
            "network": caps.network,
            "timeout_s": timeout_s,
            "cwd": str(work),
            "python": sys.version.split()[0],
            "interpreter": interp_source,
            "lockfile_sha256": lockfile_sha,
        },
        "code": {"path": str(script_path), "sha256": file_hash(script_path)},
        "data": data_fps,
        "argv": argv,
        "started_at": started,
        "finished_at": finished,
        "seeds": [seed] if seed is not None else [],
    }
    if exit_code is not None:
        record["exit_code"] = exit_code
    if missing:
        record["missing_fingerprints"] = missing

    created_rows: list[dict[str, Any]] = []
    out_json = work / "outputs" / "rows.json"
    if status == "succeeded" and out_json.is_file():
        output = json.loads(out_json.read_text(encoding="utf-8"))
        record["outputs"] = [{"path": "work/outputs/rows.json", "sha256": file_hash(out_json)}]
        created_rows = rows.append_from_output(root, run_id, output)

    errors = validate("run", record)
    if errors:
        raise ValueError(f"invalid run record: {errors}")
    (run_dir / "run.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {
        "run_id": run_id,
        "status": status,
        "exit_code": exit_code,
        "rows": len(created_rows),
        "dir": str(run_dir),
        "network": caps.network,
    }
