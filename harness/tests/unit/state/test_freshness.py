"""Freshness and invalidation over F5b (02 §6, FR-10, T09)."""

from __future__ import annotations

import json
from pathlib import Path

from research_harness.state.freshness import approval_valid, compute_stale
from research_harness.state.store import Store
from research_harness_dev.fixtures.f5b import FOLDER_A, build_f5b

HUMAN = {"kind": "human", "name": "t", "version": "0.1.0"}


def _checkpoint(root: Path) -> None:
    Store(root).checkpoint(by="human", note="mutation (synthetic)")


def _edit_json(path: Path, mutate) -> None:
    obj = json.loads(path.read_text(encoding="utf-8"))
    mutate(obj)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _approval(root: Path) -> dict:
    return json.loads((root / "approvals" / "AP-0001.json").read_text(encoding="utf-8"))


def test_baseline_all_current(tmp_path: Path) -> None:
    root = build_f5b(tmp_path / "f5b")
    assert compute_stale(root) == set()
    assert approval_valid(root, _approval(root)) is True


def test_source_hash_change(tmp_path: Path) -> None:
    root = build_f5b(tmp_path / "f5b")
    _edit_json(root / "sources" / "S-0001.json", lambda o: o["fulltext"].update(sha256="c" * 64))
    _checkpoint(root)
    stale = compute_stale(root)
    assert stale == {"excerpt:E-00001", "claim:C-0001", "check_run:CR-0001"}
    # Unrelated source branch stays current.
    assert "claim:C-0002" not in stale and "excerpt:E-00002" not in stale
    # Approval on U-A text still valid: that ref did not change.
    assert approval_valid(root, _approval(root)) is True


def test_result_value_change(tmp_path: Path) -> None:
    root = build_f5b(tmp_path / "f5b")
    _edit_json(root / "analysis" / "results" / "RR-0001-0001.json", lambda o: o.update(value=0.9))
    _checkpoint(root)
    stale = compute_stale(root)
    assert stale == {"claim:C-0003", "check_run:CR-0001"}
    assert "claim:C-0001" not in stale and "claim:C-0002" not in stale


def test_unit_text_change(tmp_path: Path) -> None:
    root = build_f5b(tmp_path / "f5b")
    (root / FOLDER_A / "text.md").write_text(
        "---\nid: U-AAAA1111\ntitle: 'Unit A'\nkind: section\n---\n\nedited body A\n",
        encoding="utf-8",
    )
    _checkpoint(root)
    stale = compute_stale(root)
    assert stale == {"claim:C-0001", "claim:C-0003", "check_run:CR-0001"}
    assert "claim:C-0002" not in stale
    # G3 approval bound to this unit's text is now invalid for the new snapshot.
    assert approval_valid(root, _approval(root)) is False


def test_rulepack_version_change(tmp_path: Path) -> None:
    root = build_f5b(tmp_path / "f5b")
    _edit_json(root / "rules" / "ua-mon-phd.json", lambda o: o.update(version="2026-11-01"))
    _checkpoint(root)
    stale = compute_stale(root)
    assert "check_run:CR-0001" in stale
    # No claim changed, so only the check run is stale.
    assert not any(s.startswith("claim:") for s in stale)
