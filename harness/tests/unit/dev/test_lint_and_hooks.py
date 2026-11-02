"""PH-4: fast `rh-dev lint` and the tracked pre-commit hook installer."""

from __future__ import annotations

import subprocess
from pathlib import Path

from research_harness_dev import check


def test_lint_steps_are_ruff_only() -> None:
    labels = [label for label, _ in check._RUFF_STEPS]
    assert labels == ["ruff check", "ruff format --check"]
    assert all("pytest" not in label for label in labels)


def test_install_hooks_sets_hooks_path(tmp_path: Path, monkeypatch) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    hooks = tmp_path / "harness" / "scripts" / "git-hooks"
    hooks.mkdir(parents=True)
    (hooks / "pre-commit").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    assert check.install_hooks_main([]) == 0

    got = subprocess.run(
        ["git", "config", "core.hooksPath"], cwd=tmp_path, capture_output=True, text=True
    )
    assert got.stdout.strip() == "harness/scripts/git-hooks"
    assert (hooks / "pre-commit").stat().st_mode & 0o111  # executable


def test_install_hooks_missing_script_fails(tmp_path: Path, monkeypatch) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    monkeypatch.chdir(tmp_path)
    assert check.install_hooks_main([]) == 1


def test_dispatcher_routes_lint_and_install_hooks(monkeypatch) -> None:
    calls = {}

    def _rec(key):
        def _fn(argv):
            calls[key] = argv
            return 0

        return _fn

    monkeypatch.setattr(check, "lint_main", _rec("lint"))
    monkeypatch.setattr(check, "install_hooks_main", _rec("hooks"))
    assert check.main(["lint", "--x"]) == 0
    assert check.main(["install-hooks"]) == 0
    assert calls == {"lint": ["--x"], "hooks": []}
