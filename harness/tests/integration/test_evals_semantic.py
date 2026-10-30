"""M2-17: semantic evaluation scorer and runner over the F4-W synthetic run.

The run artifact is synthetic (H6) so these checks are deterministic and offline;
a real host (С) run swaps in a run_kind=host artifact with a recorded model id.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from research_harness.core.errors import InvalidInputError
from research_harness.evals import metrics as M
from research_harness.evals import runner
from research_harness.schemas import validate

_H = Path(__file__).resolve().parents[2]
_ANN = _H / "evals" / "fixtures" / "F4W" / "annotation.yaml"
_RUN = _H / "evals" / "fixtures" / "F4W" / "runs" / "F4W-synthetic.run.json"


@pytest.fixture
def ann() -> dict:
    return yaml.safe_load(_ANN.read_text(encoding="utf-8"))


@pytest.fixture
def run() -> dict:
    return json.loads(_RUN.read_text(encoding="utf-8"))


def test_run_artifact_is_synthetic_and_valid(run: dict) -> None:
    assert validate("eval_run", run) == []
    assert run["run_kind"] == "synthetic" and run["synthetic"] is True  # H6: never a baseline


def test_wilson_bounds() -> None:
    w = M.wilson(0, 0)
    assert w["n"] == 0
    full = M.wilson(10, 10)
    assert full["value"] == 1.0 and full["hi"] == 1.0
    half = M.wilson(5, 10)
    assert 0.0 < half["lo"] < 0.5 < half["hi"] < 1.0


def test_mx_recall_precision(ann: dict, run: dict) -> None:
    mx = M.score("MX", ann, run)
    assert mx["recall"]["k"] == 38 and mx["recall"]["n"] == 40  # 2 material claims missed
    assert mx["precision"]["n"] == 39  # 38 true + 1 spurious extraction
    assert "lo" in mx["recall"] and "hi" in mx["recall"]  # CI present (§6)


def test_mv_accuracy_and_critical_recall(ann: dict, run: dict) -> None:
    mv = M.score("MV", ann, run)
    assert mv["critical_recall"]["value"] == 1.0  # no critical verdict error
    assert 0.0 < mv["macro_f1"] <= 1.0
    assert "supported" in mv["per_class"]


def test_ms_recall_and_missed(ann: dict, run: dict) -> None:
    ms = M.score("MS", ann, run)
    assert set(ms["missed_defects"]) == {"D6", "D12"}
    assert ms["recall"]["k"] == ms["recall"]["n"] - 2


def test_mf_zero_critical_false_pass(ann: dict, run: dict) -> None:
    mf = M.score("MF", ann, run)
    assert mf["false_pass"] == 2  # two non-critical false PASS
    assert mf["critical_false_pass"] == 0 and mf["critical_target_met"] is True


def test_ma_no_invented_position(ann: dict, run: dict) -> None:
    ma = M.score("MA", ann, run)
    assert ma["invented"] == 0 and ma["target_met"] is True


def test_suite_runs_and_passes() -> None:
    report = runner.run_suite("M2-semantic", write=False)
    assert report["all_pass"] is True
    t06 = next(r for r in report["results"] if r["id"] == "T06")
    assert t06["run_kind"] == "synthetic" and t06["metrics"]["MF"]["critical_target_met"]


def test_missing_run_artifact_is_pending(tmp_path: Path) -> None:
    from research_harness.evals.cases import Case

    case = Case(
        id="X",
        kind="semantic",
        title="t",
        nodes=[],
        fixture="F4-W",
        metrics=["MF"],
        inp={
            "annotation": "evals/fixtures/F4W/annotation.yaml",
            "run": "evals/fixtures/F4W/runs/does-not-exist.json",
        },
    )
    res = runner.run_case(case)
    assert res["passed"] is True and res["pending"] is True


def test_run_override_under_holdout_refused() -> None:
    with pytest.raises(InvalidInputError):
        runner.run_suite("M2-semantic", write=False, run_override="x/holdout/run.json")


def test_unknown_case_refused() -> None:
    with pytest.raises(InvalidInputError):
        runner.run_suite("M2-semantic", write=False, only="NOPE")
