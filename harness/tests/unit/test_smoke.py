"""Smoke tests for the M1-01 bootstrap."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from research_harness import __version__
from research_harness.cli.main import main as rh_main
from research_harness_dev.check import forbidden_hits, scan_forbidden_paths


def test_rh_version_envelope(capsys: pytest.CaptureFixture[str]) -> None:
    rc = rh_main(["version"])
    assert rc == 0
    envelope = json.loads(capsys.readouterr().out)
    assert envelope["command"] == "version"
    assert envelope["status"] == "ok"
    assert envelope["schema_version"] == "0.2"
    assert envelope["data"]["version"] == __version__


def test_rh_no_command_exits_2(capsys: pytest.CaptureFixture[str]) -> None:
    assert rh_main([]) == 2


def test_forbidden_hits_patterns() -> None:
    sample = [
        "research-harness-spec/holdout/secret.md",
        "Projects/X__A-2026-001/sources/inbox/a.pdf",
        "Projects/X__A-2026-001/sources/fulltext/b.pdf",
        "Projects/X__A-2026-001/materials/private/notes.md",
        "Projects/X__A-2026-001/.rh/lock",
        "Projects/X__A-2026-001/work/scratch.txt",
        ".env",
        "config/source-policy.local.yaml",
        "deep/nested/secrets/key.pem",
        "harness/pyproject.toml",
        "README.md",
    ]
    hits = set(forbidden_hits(sample))
    assert "harness/pyproject.toml" not in hits
    assert "README.md" not in hits
    assert hits == {
        "research-harness-spec/holdout/secret.md",
        "Projects/X__A-2026-001/sources/inbox/a.pdf",
        "Projects/X__A-2026-001/sources/fulltext/b.pdf",
        "Projects/X__A-2026-001/materials/private/notes.md",
        "Projects/X__A-2026-001/.rh/lock",
        "Projects/X__A-2026-001/work/scratch.txt",
        ".env",
        "config/source-policy.local.yaml",
        "deep/nested/secrets/key.pem",
    }


def test_scan_flags_force_added_files(tmp_path: Path) -> None:
    """A holdout or sources/inbox file force-added to git is flagged (DoD)."""

    def git(*args: str) -> None:
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)

    git("init")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "t")

    (tmp_path / "README.md").write_text("ok\n", encoding="utf-8")
    holdout = tmp_path / "research-harness-spec" / "holdout"
    holdout.mkdir(parents=True)
    (holdout / "x.md").write_text("secret\n", encoding="utf-8")
    inbox = tmp_path / "Projects" / "X__A-2026-001" / "sources" / "inbox"
    inbox.mkdir(parents=True)
    (inbox / "a.pdf").write_text("pdf\n", encoding="utf-8")

    gitignore = "**/holdout/**\nProjects/**/sources/inbox/**\n"
    (tmp_path / ".gitignore").write_text(gitignore, encoding="utf-8")

    git("add", "README.md", ".gitignore")
    git("add", "-f", "research-harness-spec/holdout/x.md")
    git("add", "-f", "Projects/X__A-2026-001/sources/inbox/a.pdf")

    hits = set(scan_forbidden_paths(tmp_path))
    assert hits == {
        "research-harness-spec/holdout/x.md",
        "Projects/X__A-2026-001/sources/inbox/a.pdf",
    }
