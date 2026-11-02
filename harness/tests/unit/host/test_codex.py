"""Codex host adapter + host parity (M3-16, NFR-13, T42)."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from research_harness.cli.main import main
from research_harness_dev import host as host_mod

_CONFIG = Path(host_mod._HARNESS) / "host" / "codex" / "config.toml"


def test_config_is_valid_toml_and_deterministic() -> None:
    text = host_mod.codex_config_text()
    assert text == host_mod.codex_config_text()  # deterministic
    data = tomllib.loads(text)
    assert data["sandbox_mode"] == "workspace-write"
    assert data["sandbox_workspace_write"]["network_access"] is False
    assert data["project_doc_max_bytes"] == 65536
    env = data["shell_environment_policy"]["set"]
    assert env == {"RH_AGENT_SESSION": "1", "RH_HOST": "codex"}
    assert data["shell_environment_policy"]["ignore_default_excludes"] is False
    deny = data["permissions"]["research-harness"]["filesystem"][":workspace_roots"]
    assert deny["**/holdout/**"] == "deny"
    assert deny["**/*.env"] == "deny"
    assert deny["**/secrets/**"] == "deny"


def test_committed_config_matches_generator() -> None:
    assert _CONFIG.is_file(), "run: rh-dev host generate codex"
    assert _CONFIG.read_text(encoding="utf-8") == host_mod.codex_config_text()


def test_generate_writes_config(tmp_path: Path) -> None:
    path = host_mod.generate_codex_config(tmp_path)
    assert path.read_text(encoding="utf-8") == host_mod.codex_config_text()


def test_cli_output_is_host_neutral(capsys: pytest.CaptureFixture[str], monkeypatch) -> None:
    # Same command, different RH_HOST -> identical CLI result (runtime-neutral, NFR-13).
    monkeypatch.setenv("RH_HOST", "claude-code")
    assert main(["version"]) == 0
    out_claude = capsys.readouterr().out
    monkeypatch.setenv("RH_HOST", "codex")
    assert main(["version"]) == 0
    out_codex = capsys.readouterr().out
    assert out_claude == out_codex
