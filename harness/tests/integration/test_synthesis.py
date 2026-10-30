"""Synthesis desk (M2-04): T30 (excerpt/premise), T60 (counter-evidence), T61 (saturation)."""

from __future__ import annotations

from pathlib import Path

from research_harness.evidence import excerpts as excerpts_mod
from research_harness.evidence import premises as premises_mod
from research_harness.lab import counter as counter_mod
from research_harness.lab import findings as findings_mod
from research_harness.lab import gaps as gaps_mod
from research_harness.lab import matrix as matrix_mod
from research_harness.lab import positions as positions_mod
from research_harness.lab import saturation as saturation_mod
from research_harness.workspace.objects import create_object
from research_harness.workspace.workspace import Workspace


def _object(tmp_path: Path):
    ws = Workspace.init(tmp_path / "Projects")
    return create_object(ws, title="Синтез", kind="article", document_kind="article")


def test_excerpt_runs_quote_check(tmp_path: Path) -> None:
    _oid, folder = _object(tmp_path)
    exc, _findings = excerpts_mod.add_excerpt(
        folder,
        source_id="S-0001",
        text="formative feedback improves learning",
        locator={"pdf_page": 1},
        access_level="fulltext",
    )
    assert exc["id"] == "E-00001"
    # No local page text yet → the quote check cannot pass; never fabricated.
    assert exc["quote_check"]["result"] in ("unknown", "fail")
    assert len(exc["source_sha256"]) == 64


def test_matrix_statement_without_excerpt_is_finding(tmp_path: Path) -> None:  # T30
    _oid, folder = _object(tmp_path)
    _row, findings = matrix_mod.add_row(
        folder,
        source_id="S-0001",
        question_id="Q1",
        statement="X improves Y",
        data_basis="RCT",
        limitations="small n",
        excerpt_ids=[],
    )
    assert any(f["check_id"] == "matrix.no_excerpt" for f in findings)
    _row2, f2 = matrix_mod.add_row(
        folder,
        source_id="S-0001",
        question_id="Q1",
        statement="X improves Y",
        data_basis="RCT",
        limitations="small n",
        excerpt_ids=["E-00001"],
    )
    assert not f2


def test_premise_without_basis_is_finding(tmp_path: Path) -> None:  # T30
    _oid, folder = _object(tmp_path)
    pre, findings = premises_mod.add_premise(folder, statement="assessment is formative")
    assert pre is None and any(f["check_id"] == "premise.no_basis" for f in findings)

    pre2, f2 = premises_mod.add_premise(folder, statement="scope assumption", assumption=True)
    assert pre2 is not None and pre2["id"] == "P-0001" and not f2
    pre3, f3 = premises_mod.add_premise(folder, statement="grounded", excerpt_ids=["E-00001"])
    assert pre3 is not None and not f3


def test_counter_not_found_needs_query(tmp_path: Path) -> None:
    _oid, folder = _object(tmp_path)
    entry, findings = counter_mod.record(
        folder, claim_ref="claim:C-0001", queries=[], outcome="not_found_after_search"
    )
    assert entry is None and any(f["check_id"] == "counter.no_query" for f in findings)
    entry2, f2 = counter_mod.record(
        folder,
        claim_ref="claim:C-0001",
        queries=["X AND counter"],
        outcome="not_found_after_search",
    )
    assert entry2 is not None and not f2


def test_findings_blocked_until_counter_evidence(tmp_path: Path) -> None:  # T60
    _oid, folder = _object(tmp_path)
    central = ["claim:C-0001"]
    blocked = findings_mod.set_findings(folder, [{"statement": "f1"}], central_claims=central)
    assert any(f["check_id"] == "findings.counter_missing" for f in blocked)
    assert not findings_mod.findings_path(folder).is_file()

    counter_mod.record(folder, claim_ref="claim:C-0001", queries=["q"], outcome="found")
    ok = findings_mod.set_findings(folder, [{"statement": "f1"}], central_claims=central)
    assert ok == [] and findings_mod.findings_path(folder).is_file()


def test_saturation_two_empty_batches_propose_stop(tmp_path: Path) -> None:  # T61
    _oid, folder = _object(tmp_path)
    for _ in range(3):  # same position each time → only the first batch adds a theme
        matrix_mod.add_row(
            folder,
            source_id="S-0001",
            question_id="Q1",
            statement="s",
            data_basis="d",
            limitations="l",
            excerpt_ids=["E-00001"],
            position="posA",
        )
    report = saturation_mod.check(folder, batch_size=1, stop_after=2)
    assert report["new_per_batch"] == [1, 0, 0]
    assert report["propose_stop"] is True and report["total_themes"] == 1


def test_position_ref_must_resolve(tmp_path: Path) -> None:
    _oid, folder = _object(tmp_path)
    findings = positions_mod.set_positions(
        folder, [{"label": "pro", "evidence_refs": ["matrix:MR-9999"]}]
    )
    assert any(f["check_id"] == "positions.unknown_ref" for f in findings)

    row, _ = matrix_mod.add_row(
        folder,
        source_id="S-0001",
        question_id="Q1",
        statement="s",
        data_basis="d",
        limitations="l",
        excerpt_ids=["E-00001"],
    )
    ok = positions_mod.set_positions(
        folder, [{"label": "pro", "evidence_refs": [f"matrix:{row['id']}"]}]
    )
    assert ok == [] and positions_mod.positions_path(folder).is_file()
    assert gaps_mod  # gaps module importable (shares ref check)
