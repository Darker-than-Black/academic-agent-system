"""Finding index + human-only resolution logic (M3-05, T13)."""

from __future__ import annotations

from pathlib import Path

import pytest

from research_harness.findings import index as fi


def _finding(check_id: str = "review.coverage_incomplete") -> dict[str, object]:
    return {"check_id": check_id, "severity": "major", "reason": "x", "location": {}}


def test_add_and_list(tmp_path: Path) -> None:
    e1 = fi.add(tmp_path, _finding(), review_id="REVIEW-1")
    fi.add(tmp_path, _finding("fulltext.crossref"), review_id="REVIEW-1")
    assert e1["id"] == "F-1" and e1["status"] == "open"
    assert len(fi.list_findings(tmp_path)) == 2
    assert len(fi.list_findings(tmp_path, status="open")) == 2
    assert fi.list_findings(tmp_path, status="accepted") == []


def test_resolve_accept(tmp_path: Path) -> None:
    fi.add(tmp_path, _finding())
    e = fi.resolve(tmp_path, "F-1", decision="accept", reason=None, by="author")
    assert e["status"] == "accepted" and e["resolutions"][-1]["decision"] == "accept"


def test_reject_requires_reason(tmp_path: Path) -> None:
    fi.add(tmp_path, _finding())
    with pytest.raises(ValueError):
        fi.resolve(tmp_path, "F-1", decision="reject", reason="", by="author")
    e = fi.resolve(tmp_path, "F-1", decision="reject", reason="not a real defect", by="author")
    assert e["status"] == "rejected" and e["resolutions"][-1]["reason"] == "not a real defect"


def test_resolutions_are_append_only(tmp_path: Path) -> None:
    fi.add(tmp_path, _finding())
    fi.resolve(tmp_path, "F-1", decision="accept", reason=None, by="author")
    e = fi.resolve(tmp_path, "F-1", decision="fixed", reason=None, by="author")
    assert len(e["resolutions"]) == 2 and e["status"] == "fixed"


def test_unknown_finding_raises(tmp_path: Path) -> None:
    with pytest.raises(KeyError):
        fi.resolve(tmp_path, "F-99", decision="accept", reason=None, by="author")
