"""Submission / publication records (M3-08, FR-28, T29a)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from research_harness.core.errors import BlockedError
from research_harness.lifecycle import records as rec


def _scaffold(tmp_path: Path, *, g3: bool = True) -> Path:
    snaps = tmp_path / ".rh" / "snapshots"
    snaps.mkdir(parents=True)
    sid = "snap-ABCDEFGHJKMNPQRSTVWXYZ0123"
    (snaps / f"{sid}.json").write_text(json.dumps({"id": sid, "files": []}), encoding="utf-8")
    (tmp_path / ".rh" / "CURRENT").write_text(sid + "\n", encoding="utf-8")
    appr = tmp_path / "approvals"
    appr.mkdir()
    if g3:
        (appr / "approvals.jsonl").write_text(
            json.dumps(
                {
                    "id": "AP-0007",
                    "gate": "G3",
                    "decision": "approved",
                    "target": {"snapshot_id": sid},
                }
            )
            + "\n",
            encoding="utf-8",
        )
    return tmp_path


def test_submission_requires_g3(tmp_path: Path) -> None:
    _scaffold(tmp_path, g3=False)
    with pytest.raises(BlockedError):
        rec.record_submission(tmp_path, venue_title="J", date="2026-11-02", channel_note="x")


def test_submission_then_publication(tmp_path: Path) -> None:
    _scaffold(tmp_path, g3=True)
    s = rec.record_submission(
        tmp_path,
        venue_title="Journal of X",
        date="2026-11-02",
        channel_note="OJS",
        issn=["1234-5678"],
        manuscript_id="JX-1",
    )
    assert s["id"] == "SUB-01" and s["g3_approval_id"] == "AP-0007"
    assert len(s["manifest_sha256"]) == 64
    assert rec.load_tags(tmp_path)["submitted:2026-11-02"] == s["snapshot_id"]

    p = rec.record_publication(
        tmp_path, submission_id="SUB-01", date="2027-02-01", doi="10.1234/x", license="CC-BY-4.0"
    )
    assert p["id"] == "PUB-01" and p["submission_id"] == "SUB-01"
    assert rec.load_tags(tmp_path)["published"] == p["snapshot_id"]


def test_no_snapshot_blocks(tmp_path: Path) -> None:
    (tmp_path / "approvals").mkdir()
    with pytest.raises(BlockedError):
        rec.record_submission(tmp_path, venue_title="J", date="2026-11-02", channel_note="x")
