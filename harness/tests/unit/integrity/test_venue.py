"""Venue status check (M3-12, FR-37, D14/T39)."""

from __future__ import annotations

from pathlib import Path

import pytest

from research_harness.core.errors import InvalidInputError
from research_harness.integrity import venue as v


def _rec(root: Path, status: str, date: str = "2026-11-02", rid_bump: str = "") -> dict:
    return v.record_check(
        root,
        title="Journal of X" + rid_bump,
        resource="scopus_sources",
        query_date=date,
        status_value=status,
        status_date=date,
        checked_by="author",
        issn=["1234-5678"],
        evidence={"url": "https://scopus.com"},
        rule_refs=["scopus-indexed"],
    )


def test_record_and_list(tmp_path: Path) -> None:
    r = _rec(tmp_path, "included")
    assert r["id"] == "VC-001"
    assert (v.checks_dir(tmp_path) / "VC-001.json").is_file()
    assert len(v.list_checks(tmp_path)) == 1


def test_included_passes(tmp_path: Path) -> None:
    _rec(tmp_path, "included")
    assert v.status_findings(tmp_path) == []


def test_not_included_blocks(tmp_path: Path) -> None:
    _rec(tmp_path, "not_included")
    f = v.status_findings(tmp_path)
    assert f[0]["check_id"] == "integrity.venue_status" and f[0]["severity"] == "blocker"


def test_unknown_is_major(tmp_path: Path) -> None:
    _rec(tmp_path, "unknown")
    assert v.status_findings(tmp_path)[0]["severity"] == "major"


def test_no_check_is_major(tmp_path: Path) -> None:
    f = v.status_findings(tmp_path)
    assert len(f) == 1 and f[0]["observed"] == "unknown"


def test_latest_wins(tmp_path: Path) -> None:
    _rec(tmp_path, "not_included", date="2026-01-01")
    _rec(tmp_path, "included", date="2026-11-02")
    assert v.status_findings(tmp_path) == []  # latest is included


def test_bad_resource_rejected(tmp_path: Path) -> None:
    with pytest.raises(InvalidInputError):
        v.record_check(
            tmp_path,
            title="J",
            resource="wikipedia",
            query_date="2026-11-02",
            status_value="included",
            status_date="2026-11-02",
            checked_by="author",
        )
