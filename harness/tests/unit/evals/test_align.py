"""Host-run alignment (M2-19): span-overlap claim_id mapping, no verdict leak.

All data here is synthetic throwaway (H6) — a tiny Latin manuscript, a synthetic
raw run and a synthetic annotation. Gold spans are computed from the manuscript
with the same paragraph logic the aligner uses, so no offsets are hand-guessed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from research_harness.core.errors import InvalidInputError
from research_harness.evals import align, metrics

MAN = """\
---
fixture: TEST
---

# Heading

Alpha beta gamma delta epsilon.

Zeta eta theta iota kappa.
"""


def _span(section: str, pi: int, sub: str) -> dict:
    p = align.paragraphs(MAN)[pi]
    s = p.index(sub)
    return {"section": section, "paragraph": pi, "start": s, "end": s + len(sub)}


ANNOTATION = {
    "fixture": "TEST",
    "claims": [
        {
            "claim_id": "C-1",
            "material": True,
            "criticality": "critical",
            "expected_verdict": "contradicted",
            "span": _span("S", 0, "beta gamma"),
        },
        {
            "claim_id": "C-2",
            "material": True,
            "criticality": "minor",
            "expected_verdict": "supported",
            "span": _span("S", 1, "theta iota"),
        },
    ],
}

RAW = {
    "schema_version": "0.2",
    "fixture": "TEST",
    "run_kind": "host",
    "producer": {"model_id": "test/model", "date": "2026-11-01"},
    "extracted": [
        {"local_id": "M-001", "material": True, "anchor": {"quote": "beta gamma delta"}},
        {"local_id": "M-002", "material": True, "anchor": {"quote": "theta iota"}},
        {"local_id": "M-003", "material": True, "anchor": {"quote": "epsilon"}},
        {"local_id": "M-004", "material": True, "anchor": {"quote": "absent phrase xyz"}},
    ],
    "reviewed": [
        {"local_id": "M-001", "verdict": "supported", "flagged_defects": ["D1"]},
        {"local_id": "M-002", "verdict": "supported"},
        {"local_id": "M-003", "verdict": "insufficient"},
    ],
    "integration_findings": [{"id": "IF-1", "defect_id": "D13"}],
    "contribution_points": [{"point_id": "CP-1", "response": "placeholder"}],
}


def test_aligns_by_span_overlap() -> None:
    res = align.align(RAW, ANNOTATION, MAN)
    run, rep = res["run"], res["report"]
    by_local = {e["claim_id"] for e in run["extracted"]}
    assert by_local == {"C-1", "C-2", None}
    assert rep["matched"] == 2
    assert rep["spurious"] == 2  # M-003 (no gold overlap) + M-004 (unresolved)
    assert rep["unresolved"] == ["M-004"]


def test_verdict_is_not_leaked_from_gold() -> None:
    # Gold expects C-1 "contradicted"; the model said "supported". The aligned
    # output must keep the MODEL's verdict, never the gold one (H6).
    run = align.align(RAW, ANNOTATION, MAN)["run"]
    c1 = next(r for r in run["reviewed"] if r["claim_id"] == "C-1")
    assert c1["verdict"] == "supported"
    assert c1["flagged_defects"] == ["D1"]
    # And the scorer then records this as a (non-critical-safe) false PASS, proving
    # the verdict came from the run, not the annotation.
    mf = metrics.score("MF", ANNOTATION, run)
    assert "C-1" in mf["false_pass_claims"]


def test_reviewed_only_holds_matched_claims() -> None:
    run = align.align(RAW, ANNOTATION, MAN)["run"]
    ids = {r["claim_id"] for r in run["reviewed"]}
    assert ids == {"C-1", "C-2"}  # M-003's verdict dropped: no gold claim
    assert all(isinstance(r["claim_id"], str) for r in run["reviewed"])


def test_findings_and_points_pass_through() -> None:
    run = align.align(RAW, ANNOTATION, MAN)["run"]
    assert run["integration_findings"] == [{"id": "IF-1", "defect_id": "D13"}]
    assert run["contribution_points"] == [{"point_id": "CP-1", "response": "placeholder"}]


def test_unresolved_quote_is_not_guessed() -> None:
    assert align.resolve(align.paragraphs(MAN), "absent phrase xyz") is None
    # Ambiguous (appears twice) is also refused.
    assert align.resolve(["a a", "b"], "a") is None


def test_align_files_seals_raw_sha256(tmp_path: Path) -> None:
    import yaml

    raw_p = tmp_path / "F4W-host.raw.json"
    ann_p = tmp_path / "annotation.yaml"
    man_p = tmp_path / "manuscript.md"
    out_p = tmp_path / "runs" / "F4W-host.run.json"
    raw_p.write_text(json.dumps(RAW), encoding="utf-8")
    ann_p.write_text(yaml.safe_dump(ANNOTATION, allow_unicode=True), encoding="utf-8")
    man_p.write_text(MAN, encoding="utf-8")

    rep = align.align_files(raw_p, ann_p, man_p, out_p)
    assert rep["matched"] == 2
    out = json.loads(out_p.read_text(encoding="utf-8"))
    note = out["producer"]["note"]
    assert "aligned_from=F4W-host.raw.json@sha256:" in note
    assert align._sha256(raw_p)[:12] in note


def test_align_files_missing_inputs(tmp_path: Path) -> None:
    with pytest.raises(InvalidInputError, match="align_no_raw"):
        align.align_files(
            tmp_path / "nope.json", tmp_path / "a.yaml", tmp_path / "m.md", tmp_path / "o.json"
        )
