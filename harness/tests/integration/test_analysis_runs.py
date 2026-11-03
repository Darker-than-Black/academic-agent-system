"""Sandbox runs, result rows and tuple validators (M3-19; analysis-sandbox.md;
ADR-009; T04/T05 shape). Deterministic; the run has the network off."""

from __future__ import annotations

import json
from pathlib import Path

from research_harness.analysis import rows as rows_mod
from research_harness.analysis import runner, tuples

_ROWS_SCRIPT = """\
import json, os
os.makedirs("outputs", exist_ok=True)
with open("outputs/rows.json", "w", encoding="utf-8") as fh:
    json.dump([
        {"dataset_id": "D-001", "subset": "all", "condition": "base",
         "variable_or_metric": "accuracy", "value": 0.95, "unit": "ratio",
         "aggregation": "mean"}
    ], fh)
print("done")
"""

_FAIL_SCRIPT = "import sys; sys.exit(2)\n"

_NET_SCRIPT = """\
import json, os, socket
os.makedirs("outputs", exist_ok=True)
blocked = False
try:
    socket.create_connection(("93.184.216.34", 80), timeout=2)
except OSError:
    blocked = True
with open("outputs/rows.json", "w", encoding="utf-8") as fh:
    json.dump([{"variable_or_metric": "blocked", "value": int(blocked),
                "unit": "bool", "aggregation": "none"}], fh)
"""


def _script(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "script.py"
    p.write_text(body, encoding="utf-8")
    return p


def test_interpreter_defaults_to_harness(tmp_path: Path) -> None:
    import sys

    from research_harness.analysis import project

    interp, source = runner._interpreter(tmp_path)
    assert source == "harness" and interp == sys.executable
    # Provenance field reflects the fallback.
    _ = project.project_dir  # keep import meaningful


def test_interpreter_prefers_analysis_venv(tmp_path: Path) -> None:
    from research_harness.analysis import project

    venv_py = project.project_dir(tmp_path) / ".venv" / "bin" / "python"
    venv_py.parent.mkdir(parents=True, exist_ok=True)
    venv_py.write_text("#!/bin/sh\n", encoding="utf-8")
    interp, source = runner._interpreter(tmp_path)
    assert source == "analysis-venv" and interp == str(venv_py)


def test_run_records_interpreter(tmp_path: Path) -> None:
    report = runner.run(tmp_path, _script(tmp_path, _ROWS_SCRIPT))
    run_json = json.loads((Path(report["dir"]) / "run.json").read_text(encoding="utf-8"))
    assert run_json["sandbox"]["interpreter"] in ("analysis-venv", "harness")


def test_run_produces_rows(tmp_path: Path) -> None:
    report = runner.run(tmp_path, _script(tmp_path, _ROWS_SCRIPT))
    assert report["status"] == "succeeded" and report["rows"] == 1
    assert report["network"] in ("disabled", "guard_only")
    run_json = json.loads((Path(report["dir"]) / "run.json").read_text(encoding="utf-8"))
    assert run_json["network"] == "disabled"
    assert run_json["sandbox"]["network"] in ("disabled", "guard_only")
    row = rows_mod.load(tmp_path)[0]
    assert row["value"] == 0.95 and row["id"].startswith("RR-0001-")


def test_failed_run_has_no_rows(tmp_path: Path) -> None:
    report = runner.run(tmp_path, _script(tmp_path, _FAIL_SCRIPT))
    assert report["status"] == "failed" and report["exit_code"] == 2
    assert report["rows"] == 0 and rows_mod.load(tmp_path) == []


def test_run_has_network_off(tmp_path: Path) -> None:
    runner.run(tmp_path, _script(tmp_path, _NET_SCRIPT))
    row = rows_mod.load(tmp_path)[0]
    assert row["value"] == 1  # the script could not open an outbound connection


# --- tuple validators ------------------------------------------------------
_ROW = {
    "id": "RR-0001-0001",
    "dataset_id": "D-001",
    "subset": "grade8",
    "condition": "base",
    "variable_or_metric": "accuracy",
    "value": 0.95,
    "unit": "ratio",
    "aggregation": "mean",
}


def _claim(**over):
    base = {
        "id": "C-1",
        "kind": "own_numeric",
        "result_ref": "RR-0001-0001",
        "expected_tuple": {
            "dataset_id": "D-001",
            "split_id": "grade8",
            "condition": "base",
            "metric_id": "accuracy",
            "unit": "ratio",
            "aggregation": "mean",
        },
    }
    base.update(over)
    return base


def test_matching_claim_passes() -> None:
    assert tuples.check_claim(_claim(shown_value=0.95), {"RR-0001-0001": _ROW}) == []


def test_wrong_subsample_is_tuple_mismatch() -> None:
    c = _claim()
    c["expected_tuple"]["split_id"] = "grade9"
    out = tuples.check_claim(c, {"RR-0001-0001": _ROW})
    assert any(f["check_id"] == "analysis.tuple_mismatch" for f in out)


def test_unit_pp_vs_ratio_is_unit_mismatch() -> None:
    c = _claim()
    c["expected_tuple"]["unit"] = "p.p."
    out = tuples.check_claim(c, {"RR-0001-0001": _ROW})
    assert any(f["check_id"] == "analysis.unit_mismatch" for f in out)


def test_implicit_x100_is_blocked() -> None:
    out = tuples.check_claim(_claim(shown_value=95), {"RR-0001-0001": _ROW})
    assert any(f["check_id"] == "analysis.implicit_conversion" for f in out)


def test_declared_factor_passes() -> None:
    c = _claim(shown_value=95, transform={"factor": 100, "expression": "value*100"})
    assert tuples.check_claim(c, {"RR-0001-0001": _ROW}) == []


def test_unresolved_result_ref_is_mismatch() -> None:
    out = tuples.check_claim(_claim(result_ref="RR-9999-9999"), {"RR-0001-0001": _ROW})
    assert out and out[0]["check_id"] == "analysis.tuple_mismatch"
