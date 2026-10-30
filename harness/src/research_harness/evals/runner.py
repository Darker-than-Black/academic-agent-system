"""Run an evaluation suite: regenerate fixtures, run each case, collect results."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import Any

from research_harness.evals.cases import Case, load_suite

_HARNESS = Path(__file__).resolve().parents[3]
RESULTS_DIR = _HARNESS / "evals" / "results"


def _run_pytest(nodes: list[str]) -> tuple[bool, int]:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider", *nodes],
        cwd=_HARNESS,
        capture_output=True,
        text=True,
        env={**_env()},
    )
    return proc.returncode == 0, proc.returncode


def _env() -> dict[str, str]:
    import os

    e = dict(os.environ)
    e["RH_TEST_MODE"] = "1"  # test-only migration (T40)
    return e


def run_case(case: Case) -> dict[str, Any]:
    if case.kind == "semantic":
        return _run_semantic(case)
    if case.kind != "pytest":
        return {
            "id": case.id,
            "title": case.title,
            "passed": False,
            "evidence": "unsupported case kind",
        }
    passed, code = _run_pytest(case.nodes)
    return {
        "id": case.id,
        "title": case.title,
        "kind": case.kind,
        "nodes": case.nodes,
        "passed": passed,
        "exit_code": code,
        "evidence": f"pytest {' '.join(case.nodes)} → exit {code}",
    }


def _run_semantic(case: Case) -> dict[str, Any]:
    """Score a semantic case against a run artifact (05-eval-base §6).

    The run artifact is produced by host subagents (С run); the core only scores
    (H5). With no artifact the case is PENDING, not a failure — the same stance as
    the holdout, which only the author runs.
    """
    import json

    import yaml

    from research_harness.evals import metrics as M
    from research_harness.schemas import validate

    base = {"id": case.id, "title": case.title, "kind": case.kind, "fixture": case.fixture}
    ann_path = _HARNESS / case.inp.get("annotation", "")
    run_path = _HARNESS / case.inp.get("run", "")
    if not ann_path.is_file():
        return {
            **base,
            "passed": False,
            "evidence": f"annotation not found: {case.inp.get('annotation')}",
        }
    if not run_path.is_file():
        return {
            **base,
            "passed": True,
            "pending": True,
            "evidence": f"PENDING: no run artifact at {case.inp.get('run')} — С run by host "
            "(08-evals-runbook §3); deterministic machinery only",
        }

    annotation = yaml.safe_load(ann_path.read_text(encoding="utf-8"))
    run = json.loads(run_path.read_text(encoding="utf-8"))
    schema_errors = validate("eval_run", run)
    if schema_errors:
        return {
            **base,
            "passed": False,
            "evidence": f"run artifact schema invalid: {schema_errors[0]}",
        }

    scores = {metric: M.score(metric, annotation, run) for metric in case.metrics}
    # Hard gate checks (M2 baseline): MF critical false-PASS must be 0; MA no invented position.
    hard: list[str] = []
    if "MF" in scores and not scores["MF"]["critical_target_met"]:
        hard.append(f"MF: {scores['MF']['critical_false_pass']} critical false PASS (must be 0)")
    if "MA" in scores and not scores["MA"]["target_met"]:
        hard.append(f"MA: {scores['MA']['invented']} invented contribution positions (must be 0)")
    # Explicit thresholds declared on the case (e.g. a lower-bound at M3/M5).
    for key, floor in case.thresholds.items():
        got = _threshold_value(scores, key)
        if got is not None and got < floor:
            hard.append(f"{key}: {got} < threshold {floor}")

    run_kind = run.get("run_kind", "host")
    warn = " [SYNTHETIC — not a gate baseline]" if run_kind == "synthetic" else ""
    passed = not hard
    evidence = (
        f"scored {','.join(case.metrics)} against {case.inp.get('run')}"
        f" (model={run.get('producer', {}).get('model_id', '?')}){warn}"
    )
    if hard:
        evidence += " — FAIL: " + "; ".join(hard)
    return {
        **base,
        "passed": passed,
        "run_kind": run_kind,
        "metrics": scores,
        "hard_failures": hard,
        "evidence": evidence,
    }


def _threshold_value(scores: dict, key: str) -> float | None:
    """Resolve a dotted threshold key like 'MV.critical_recall' or 'MX.recall'."""
    parts = key.split(".")
    node: Any = scores.get(parts[0])
    for p in parts[1:]:
        if isinstance(node, dict):
            node = node.get(p)
    if isinstance(node, dict) and "value" in node:
        node = node["value"]
    return node if isinstance(node, (int, float)) else None


def run_suite(
    suite: str, *, write: bool = True, only: str | None = None, run_override: str | None = None
) -> dict[str, Any]:
    from research_harness.core.errors import InvalidInputError

    if run_override and "holdout" in run_override:
        raise InvalidInputError("error.eval_holdout")  # H1
    cases = load_suite(suite)
    if only:
        cases = [c for c in cases if c.id == only]
        if not cases:
            raise InvalidInputError("error.eval_unknown_case")
    if run_override:
        cases = [
            replace(c, inp={**c.inp, "run": run_override}) if c.kind == "semantic" else c
            for c in cases
        ]
    results = [run_case(c) for c in cases]
    passed = sum(1 for r in results if r["passed"])
    pending = sum(1 for r in results if r.get("pending"))
    report = {
        "suite": suite,
        "date": date.today().isoformat(),
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "pending": pending,
        "all_pass": passed == len(results),
        "results": results,
    }
    if write:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        out = RESULTS_DIR / f"{suite}-{report['date']}.json"
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report["path"] = str(out.relative_to(_HARNESS))
    return report


def latest_report(suite: str) -> dict[str, Any] | None:
    if not RESULTS_DIR.is_dir():
        return None
    files = sorted(RESULTS_DIR.glob(f"{suite}-*.json"))
    if not files:
        return None
    return json.loads(files[-1].read_text(encoding="utf-8"))
