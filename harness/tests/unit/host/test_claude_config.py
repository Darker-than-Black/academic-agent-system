"""Claude Code adapter config parses; deny covers holdout; AGENTS.md lists H1–H15."""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]


def test_settings_parses_and_denies_holdout() -> None:
    settings = json.loads((REPO / ".claude" / "settings.json").read_text(encoding="utf-8"))
    deny = settings["permissions"]["deny"]
    assert "Read(**/holdout/**)" in deny
    assert any("holdout" in d for d in deny)
    assert settings["env"]["RH_AGENT_SESSION"] == "1"
    assert settings["env"]["RH_HOST"] == "claude-code"


def test_claude_md_imports_agents_only() -> None:
    text = (REPO / "CLAUDE.md").read_text(encoding="utf-8").strip()
    assert text == "@AGENTS.md"


def test_agents_md_mentions_every_hard_rule() -> None:
    text = (REPO / "AGENTS.md").read_text(encoding="utf-8")
    for n in range(1, 16):
        assert f"H{n} " in text or f"**H{n} " in text, f"AGENTS.md missing H{n}"


def test_entry_commands_exist() -> None:
    cmds = REPO / "harness" / "host" / "claude-code" / "commands"
    for name in ("start", "continue", "status", "intake"):
        f = cmds / f"{name}.md"
        assert f.is_file() and f.read_text(encoding="utf-8").strip()
