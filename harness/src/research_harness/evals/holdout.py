"""Holdout run mode (05-eval-base §5.2, §9; H1, H8) — author only.

Runs the holdout cases from a decrypted package **outside** the repo, verifies
the file set against ``harness/evals/holdout.lock.json``, and appends **only
aggregate** metrics to ``harness/evals/results/holdout-log.jsonl``. No per-case
result, case id, case title, claim id, verdict or defect is written to disk or
returned in the envelope — metric scores are sanitized to numbers before they
leave this module.

The agent never runs this; the author runs it in his own terminal (H14). The
run artifact for semantic scoring is a host С run (H5: the core only scores).
On M2 the first run is report-only: with no artifact the cases are pending, not
failures.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from research_harness.core.errors import InvalidInputError
from research_harness.evals import cases as _cases
from research_harness.evals import metrics as _M

_HARNESS = Path(__file__).resolve().parents[3]
LOCK_PATH = _HARNESS / "evals" / "holdout.lock.json"
LOG_PATH = _HARNESS / "evals" / "results" / "holdout-log.jsonl"

_SKIP = {".git", ".DS_Store", "holdout.lock.json"}


def _log_ref() -> str:
    try:
        return str(LOG_PATH.relative_to(_HARNESS))
    except ValueError:
        return str(LOG_PATH)


# --- integrity ---------------------------------------------------------------
def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def inside_repo(directory: Path) -> bool:
    """True if ``directory`` resolves inside a git work tree (H1 guard)."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=directory,
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
    root = Path(result.stdout.strip()).resolve()
    here = directory.resolve()
    return root == here or root in here.parents


def _actual_files(directory: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for p in sorted(directory.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(directory)
        if any(part in _SKIP for part in rel.parts):
            continue
        out[rel.as_posix()] = _sha256(p)
    return out


def verify_set(directory: Path, lock: dict) -> str:
    """Check ``directory`` matches the lock exactly; return a combined set hash.

    Raises ``InvalidInputError('error.holdout_set_mismatch')`` if any file is
    missing, extra, or hashes differently from ``holdout.lock.json``.
    """
    want = {f["path"]: f["sha256"] for f in lock.get("files", [])}
    got = _actual_files(directory)
    if want != got:
        raise InvalidInputError("error.holdout_set_mismatch")
    joined = "\n".join(f"{p}:{want[p]}" for p in sorted(want))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


# --- scoring (directory-relative; never via run_case, H1) --------------------
def _score_case(case: _cases.Case, directory: Path, run_override: str | None) -> dict[str, Any]:
    """Score one semantic holdout case; return numbers only, no ids/titles."""
    if case.kind != "semantic":
        return {"pending": True, "scores": {}, "model_id": None, "run_kind": None}
    ann_rel = case.inp.get("annotation", "annotation.yaml")
    ann_path = directory / ann_rel
    if run_override:
        run_path = Path(run_override)
    elif case.inp.get("run"):
        run_path = directory / case.inp["run"]
    else:
        run_path = None
    if not ann_path.is_file() or run_path is None or not run_path.is_file():
        return {"pending": True, "scores": {}, "model_id": None, "run_kind": None}
    annotation = yaml.safe_load(ann_path.read_text(encoding="utf-8"))
    run = json.loads(run_path.read_text(encoding="utf-8"))
    scores = {m: _M.score(m, annotation, run) for m in case.metrics}
    return {
        "pending": False,
        "scores": scores,
        "model_id": run.get("producer", {}).get("model_id"),
        "run_kind": run.get("run_kind", "host"),
        "thresholds": case.thresholds,
    }


def _kn(wilson: dict) -> tuple[int, int]:
    n = int(wilson.get("n", 0))
    return round(wilson.get("value", 0.0) * n), n


def _combine(parts: list[dict]) -> dict:
    k = sum(_kn(w)[0] for w in parts)
    n = sum(_kn(w)[1] for w in parts)
    return _M.wilson(k, n)


def _aggregate(scored: list[dict]) -> tuple[dict, list[str]]:
    """Combine metric scores across cases into id-free aggregates + hard fails."""
    mx_r, mx_p, mv_a, mv_c, ms_r, ms_p = ([] for _ in range(6))
    mf_fp = mf_cfp = 0
    ma_inv = ma_n = 0
    has_mf = has_ma = False
    hard: list[str] = []
    for r in scored:
        for name, sc in r["scores"].items():
            if name == "MX":
                mx_r.append(sc["recall"])
                mx_p.append(sc["precision"])
            elif name == "MV":
                mv_a.append(sc["accuracy"])
                mv_c.append(sc["critical_recall"])
            elif name == "MS":
                ms_r.append(sc["recall"])
                ms_p.append(sc["precision"])
            elif name == "MF":
                has_mf = True
                mf_fp += sc["false_pass"]
                mf_cfp += sc["critical_false_pass"]
            elif name == "MA":
                has_ma = True
                ma_inv += sc["invented"]
                ma_n += sc["n"]
        for key, floor in r.get("thresholds", {}).items():
            metric = r["scores"].get(key.split(".")[0])
            val = _threshold_value(metric, key.split(".")[1:]) if metric else None
            if val is not None and val < floor:
                hard.append(f"{key} < {floor}")
    agg: dict[str, Any] = {}
    if mx_r:
        agg["MX"] = {"recall": _combine(mx_r), "precision": _combine(mx_p)}
    if mv_a:
        agg["MV"] = {"accuracy": _combine(mv_a), "critical_recall": _combine(mv_c)}
    if ms_r:
        agg["MS"] = {"recall": _combine(ms_r), "precision": _combine(ms_p)}
    if has_mf:
        agg["MF_critical"] = {
            "false_pass": mf_fp,
            "critical_false_pass": mf_cfp,
            "critical_target_met": mf_cfp == 0,
        }
        if mf_cfp:
            hard.append(f"MF: {mf_cfp} critical false PASS (must be 0)")
    if has_ma:
        agg["MA"] = {"n": ma_n, "invented": ma_inv, "target_met": ma_inv == 0}
        if ma_inv:
            hard.append(f"MA: {ma_inv} invented positions (must be 0)")
    return agg, hard


def _threshold_value(metric: dict, parts: list[str]) -> float | None:
    node: Any = metric
    for p in parts:
        node = node.get(p) if isinstance(node, dict) else None
    if isinstance(node, dict) and "value" in node:
        node = node["value"]
    return node if isinstance(node, (int, float)) else None


# --- public API --------------------------------------------------------------
def run(directory: Path, *, run_override: str | None = None, write: bool = True) -> dict[str, Any]:
    directory = directory.expanduser().resolve()
    if not directory.is_dir():
        raise InvalidInputError("error.holdout_no_dir")
    if inside_repo(directory):
        raise InvalidInputError("error.holdout_inside_repo")
    if not LOCK_PATH.is_file():
        raise InvalidInputError("error.holdout_no_lock")
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    set_hash = verify_set(directory, lock)

    # Case files come from the verified lock, so only the locked set is run.
    case_files = [
        directory / f["path"]
        for f in lock.get("files", [])
        if f["path"].endswith(".yaml") and "cases/" in f["path"]
    ]
    if not case_files:
        raise InvalidInputError("error.holdout_no_cases")
    cases = [_cases.parse_case(p) for p in case_files]

    scored = [_score_case(c, directory, run_override) for c in cases]
    done = [s for s in scored if not s["pending"]]
    pending = len(scored) - len(done)
    agg, hard = _aggregate(done)
    model_id = next((s["model_id"] for s in done if s.get("model_id")), None)
    run_kind = next((s["run_kind"] for s in done if s.get("run_kind")), None)
    all_pass = not hard

    row = {
        "date": date.today().isoformat(),
        "event": "run",
        "fixture": lock.get("fixture", "F4-H"),
        "lock_sha256": _sha256(LOCK_PATH),
        "set_hash": set_hash,
        "model_id": model_id,
        "run_kind": run_kind,
        "cases": {"total": len(cases), "scored": len(done), "pending": pending},
        "metrics": agg,
        "hard_failures": hard,
        "all_pass": all_pass,
    }
    if write:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        row["log"] = _log_ref()
    return row


def mark_compromised(reason: str, *, write: bool = True) -> dict[str, Any]:
    row = {"date": date.today().isoformat(), "event": "compromised", "reason": reason}
    if write:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        row["log"] = _log_ref()
    return row
