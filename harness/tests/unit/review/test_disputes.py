"""Disputes: cycle cap, no auto-resolve (M3-05, T23)."""

from __future__ import annotations

from pathlib import Path

import pytest

from research_harness.review import disputes as d


def test_open_and_add_cycles(tmp_path: Path) -> None:
    rec = d.open_(tmp_path, claim_id="C-1", finding_id="F-1")
    assert rec["id"] == "D-1" and rec["status"] == "open" and rec["max_cycles"] == 2
    rec = d.add_evidence(tmp_path, "D-1", by="analyst", argument="a", evidence_refs=["excerpt:E1"])
    assert len(rec["cycles"]) == 1 and not d.cap_reached(rec)
    rec = d.add_evidence(tmp_path, "D-1", by="critic", argument="b", evidence_refs=[])
    assert len(rec["cycles"]) == 2 and d.cap_reached(rec)


def test_cap_blocks_further_evidence(tmp_path: Path) -> None:
    d.open_(tmp_path, claim_id="C-1", finding_id="F-1", max_cycles=2)
    d.add_evidence(tmp_path, "D-1", by="analyst", argument="a", evidence_refs=[])
    d.add_evidence(tmp_path, "D-1", by="critic", argument="b", evidence_refs=[])
    with pytest.raises(ValueError):
        d.add_evidence(tmp_path, "D-1", by="analyst", argument="c", evidence_refs=[])


def test_close_unresolved_then_no_more_evidence(tmp_path: Path) -> None:
    d.open_(tmp_path, claim_id="C-1", finding_id="F-1")
    rec = d.close(tmp_path, "D-1", status="unresolved")
    assert rec["status"] == "unresolved"
    with pytest.raises(ValueError):
        d.add_evidence(tmp_path, "D-1", by="analyst", argument="x", evidence_refs=[])


def test_close_resolved_by_author(tmp_path: Path) -> None:
    d.open_(tmp_path, claim_id="C-1", finding_id="F-1")
    rec = d.close(tmp_path, "D-1", status="resolved_by_author", author_decision="finding accepted")
    assert rec["status"] == "resolved_by_author" and rec["author_decision"] == "finding accepted"


def test_bad_close_status_raises(tmp_path: Path) -> None:
    d.open_(tmp_path, claim_id="C-1", finding_id="F-1")
    with pytest.raises(ValueError):
        d.close(tmp_path, "D-1", status="passed")
