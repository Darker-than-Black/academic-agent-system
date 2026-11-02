"""F8 — analysis fixture: a synthetic dataset with terms, one executed result
row, and two own-numeric claims (M3-22, T04/T05-tuple/T18/T62).

One claim quotes the row correctly; the other shows the value scaled ×100 with
no declared transform, which the tuple validator flags as
``analysis.implicit_conversion`` (ADR-009 — no implicit ×100/÷100). The dataset
and row are synthetic (H6); nothing is executed here.
"""

from __future__ import annotations

import json
from pathlib import Path

from research_harness.analysis import datasets as datasets_mod

ROW_ID = "RR-0001-0001"
RUN_ID = "R-0001"

_ROW = {
    "schema_version": "0.2",
    "id": ROW_ID,
    "created_at": "2026-05-01T00:00:00Z",
    "producer": "machine",
    "run_id": RUN_ID,
    "dataset_id": "DS-001",
    "subset": "test",
    "condition": "baseline",
    "variable_or_metric": "accuracy",
    "value": 0.5,
    "unit": "fraction",
    "aggregation": "mean",
    "n": 100,
}

_TUPLE = {
    "dataset_id": "DS-001",
    "split_id": "test",
    "condition": "baseline",
    "metric_id": "accuracy",
    "unit": "fraction",
    "aggregation": "mean",
}

CLAIMS = {
    "claims": [
        {
            "id": "CL-OK",
            "kind": "own_numeric",
            "text": "Accuracy on the test split is 0.5.",
            "result_ref": ROW_ID,
            "expected_tuple": dict(_TUPLE),
            "shown_value": 0.5,
        },
        {
            # N2 defect: 50 is an undeclared ×100 of the row's 0.5 (no transform).
            "id": "CL-SCALE",
            "kind": "own_numeric",
            "text": "Accuracy on the test split is 50.",
            "result_ref": ROW_ID,
            "expected_tuple": dict(_TUPLE),
            "shown_value": 50,
        },
    ]
}


def build_f8(dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    datasets_mod.add(
        dest,
        name="synthetic-terms-set",
        version="1.0",
        terms="cc-by-4.0",
        synthetic=True,
    )
    rows = dest / "results"
    rows.mkdir(parents=True, exist_ok=True)
    (rows / "rows.jsonl").write_text(json.dumps(_ROW, ensure_ascii=False) + "\n", encoding="utf-8")
    man = dest / "manuscript"
    man.mkdir(parents=True, exist_ok=True)
    (man / "claims.json").write_text(
        json.dumps(CLAIMS, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return dest
