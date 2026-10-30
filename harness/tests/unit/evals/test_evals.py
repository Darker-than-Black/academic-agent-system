"""Eval case loading, holdout refusal, report rendering (M1-15). The full suite
is exercised by `rh eval run`, not here (it would spawn nested pytest)."""

from __future__ import annotations

import pytest

from research_harness.core.errors import InvalidInputError
from research_harness.evals import cases as cases_mod
from research_harness.evals import report as report_mod


def test_m1_suite_has_all_exit_tests() -> None:
    cases = cases_mod.load_suite("M1")
    ids = {c.id for c in cases}
    expected = {
        "T01",
        "T09",
        "T10",
        "T11",
        "T15",
        "T24",
        "T26",
        "T27",
        "T28",
        "T29",
        "T29a",
        "T37",
        "T38",
        "T40",
        "T44",
        "T45",
        "T50",
    }
    assert expected <= ids
    assert all(c.nodes for c in cases)


def test_holdout_case_is_refused() -> None:
    with pytest.raises(InvalidInputError):
        cases_mod._check_no_holdout(["research-harness-spec/holdout/secret.py::test_x"])


def test_report_text_marks_pass_and_fail() -> None:
    report = {
        "suite": "M1",
        "date": "2026-10-30",
        "total": 2,
        "passed": 1,
        "failed": 1,
        "all_pass": False,
        "results": [
            {"id": "T01", "title": "a", "passed": True, "evidence": "ok"},
            {"id": "T09", "title": "b", "passed": False, "evidence": "pytest … → exit 1"},
        ],
    }
    text = report_mod.render_text(report)
    assert "[pass] T01" in text and "[FAIL] T09" in text
