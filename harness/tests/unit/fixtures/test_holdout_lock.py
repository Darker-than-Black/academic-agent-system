"""holdout.lock.json builder (05-eval-base §5.2, §9).

Uses only synthetic throwaway files in tmp_path — never real holdout content.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from research_harness_dev.fixtures.holdout_lock import build_lock


def _pkg(root: Path) -> None:
    (root / "manuscript.md").write_text("# synthetic\n", encoding="utf-8")
    (root / "annotation.yaml").write_text("fixture: TEST\nclaims: []\n", encoding="utf-8")
    cases = root / "cases"
    cases.mkdir()
    (cases / "T06-TEST-001.yaml").write_text("id: T06-TEST-001\ntest: T06\n", encoding="utf-8")
    (cases / "T30-TEST-002.yaml").write_text("id: T30-TEST-002\ntest: T30\n", encoding="utf-8")


def test_lock_shape_and_hashes(tmp_path: Path) -> None:
    pkg = tmp_path / "F4-H"
    pkg.mkdir()
    _pkg(pkg)
    lock = build_lock(pkg)
    assert lock["schema_version"] == "0.2"
    assert lock["fixture"] == "F4-H"
    assert lock["case_ids"] == ["T06-TEST-001", "T30-TEST-002"]
    paths = {f["path"] for f in lock["files"]}
    assert paths == {
        "manuscript.md",
        "annotation.yaml",
        "cases/T06-TEST-001.yaml",
        "cases/T30-TEST-002.yaml",
    }
    assert all(len(f["sha256"]) == 64 for f in lock["files"])


def test_deterministic(tmp_path: Path) -> None:
    pkg = tmp_path / "F4-H"
    pkg.mkdir()
    _pkg(pkg)
    assert build_lock(pkg, created="2026-11-01") == build_lock(pkg, created="2026-11-01")


def test_refuses_dir_inside_repo() -> None:
    # The repo root itself is inside a git work tree; must be refused (H1).
    repo_root = Path(__file__).resolve().parents[4]
    assert (repo_root / ".git").exists()
    with pytest.raises(ValueError, match="inside a git repo"):
        build_lock(repo_root)


def test_refuses_empty_dir(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(ValueError, match="no files"):
        build_lock(empty)
