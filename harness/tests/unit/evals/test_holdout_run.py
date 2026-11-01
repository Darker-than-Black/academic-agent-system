"""Holdout run mode (M2-18): aggregates only, no per-case ids/content (H1, H8).

Everything here is synthetic throwaway data in tmp_path — never real holdout
content. LOCK_PATH/LOG_PATH are redirected into tmp_path.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from research_harness.core.errors import InvalidInputError
from research_harness.evals import holdout

_ANNOTATION = """\
fixture: TEST
claims:
  - claim_id: C-1
    material: true
    criticality: critical
    expected_verdict: contradicted
    defect_id: D13
  - claim_id: C-2
    material: true
    criticality: major
    expected_verdict: insufficient
    defect_id: D2
"""

_RUN = {
    "schema_version": "0.2",
    "fixture": "TEST",
    "run_kind": "host",
    "producer": {"model_id": "test/model", "date": "2026-11-01"},
    "extracted": [{"claim_id": "C-1", "material": True}, {"claim_id": "C-2", "material": True}],
    "reviewed": [
        {"claim_id": "C-1", "verdict": "contradicted", "flagged_defects": ["D13"]},
        {"claim_id": "C-2", "verdict": "supported", "flagged_defects": []},  # false PASS, non-crit
    ],
    "integration_findings": [],
    "contribution_points": [],
}

_CASE = """\
id: T06-TEST-001
test: T06
fixture: TEST
set: holdout
kind: semantic
metric: [MX, MV, MS, MF]
input:
  annotation: annotation.yaml
  run: run.json
"""


def _pkg(root: Path) -> None:
    (root / "annotation.yaml").write_text(_ANNOTATION, encoding="utf-8")
    (root / "run.json").write_text(json.dumps(_RUN), encoding="utf-8")
    (root / "cases").mkdir()
    (root / "cases" / "T06-TEST-001.yaml").write_text(_CASE, encoding="utf-8")


def _write_lock(pkg: Path, lock_path: Path) -> None:
    files = sorted(p for p in pkg.rglob("*") if p.is_file())
    lock = {
        "schema_version": "0.2",
        "fixture": "F4-H",
        "created": "2026-11-01",
        "case_ids": ["T06-TEST-001"],
        "files": [
            {"path": p.relative_to(pkg).as_posix(), "sha256": holdout._sha256(p)} for p in files
        ],
    }
    lock_path.write_text(json.dumps(lock), encoding="utf-8")


@pytest.fixture
def staged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    pkg = tmp_path / "F4-H"
    pkg.mkdir()
    _pkg(pkg)
    lock_path = tmp_path / "holdout.lock.json"
    _write_lock(pkg, lock_path)
    monkeypatch.setattr(holdout, "LOCK_PATH", lock_path)
    monkeypatch.setattr(holdout, "LOG_PATH", tmp_path / "holdout-log.jsonl")
    return pkg


def test_aggregates_and_no_ids_leak(staged: Path) -> None:
    row = holdout.run(staged)
    assert row["event"] == "run"
    assert row["cases"] == {"total": 1, "scored": 1, "pending": 0}
    assert row["model_id"] == "test/model"
    # MF non-critical false PASS only → critical target met, all_pass True.
    assert row["metrics"]["MF_critical"]["critical_false_pass"] == 0
    assert row["all_pass"] is True
    # MS recall = 1/2 (D13 caught, D2 missed), as an aggregate number.
    assert row["metrics"]["MS"]["recall"]["value"] == pytest.approx(0.5)
    # No claim id / defect id / case id / title anywhere in the logged row.
    blob = json.dumps(row, ensure_ascii=False)
    for leak in ("C-1", "C-2", "D2", "D13", "T06-TEST-001"):
        assert leak not in blob, f"leaked {leak}"


def test_log_line_appended(staged: Path) -> None:
    holdout.run(staged)
    holdout.run(staged)
    lines = holdout.LOG_PATH.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert all(json.loads(line)["event"] == "run" for line in lines)


def test_pending_without_artifact(staged: Path) -> None:
    (staged / "run.json").unlink()
    _write_lock(staged, holdout.LOCK_PATH)  # re-lock without the artifact
    row = holdout.run(staged)
    assert row["cases"]["pending"] == 1
    assert row["cases"]["scored"] == 0
    assert row["all_pass"] is True  # report-only, nothing failed
    assert row["metrics"] == {}


def test_refuses_dir_inside_repo(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(holdout, "LOCK_PATH", tmp_path / "x.json")
    repo_root = Path(__file__).resolve().parents[4]
    assert (repo_root / ".git").exists()
    with pytest.raises(InvalidInputError, match="holdout_inside_repo"):
        holdout.run(repo_root)


def test_refuses_set_mismatch(staged: Path) -> None:
    (staged / "annotation.yaml").write_text(_ANNOTATION + "\n# tampered\n", encoding="utf-8")
    with pytest.raises(InvalidInputError, match="holdout_set_mismatch"):
        holdout.run(staged)


def test_mark_compromised(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(holdout, "LOG_PATH", tmp_path / "holdout-log.jsonl")
    row = holdout.mark_compromised("content pasted into agent chat")
    assert row["event"] == "compromised"
    line = json.loads(holdout.LOG_PATH.read_text(encoding="utf-8").strip())
    assert line["reason"] == "content pasted into agent chat"
