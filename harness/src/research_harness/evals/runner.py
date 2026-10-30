"""Run an evaluation suite: regenerate fixtures, run each case, collect results."""

from __future__ import annotations

import json
import subprocess
import sys
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


def run_suite(suite: str, *, write: bool = True) -> dict[str, Any]:
    cases = load_suite(suite)
    results = [run_case(c) for c in cases]
    passed = sum(1 for r in results if r["passed"])
    report = {
        "suite": suite,
        "date": date.today().isoformat(),
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
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
