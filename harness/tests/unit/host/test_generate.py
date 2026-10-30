"""Claude Code adapter v1: generated subagents, config validity, downgrade (M2-13, T63)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from research_harness.models import config as model_config
from research_harness_dev import host as host_mod

_HOST = host_mod._HARNESS / "host" / "claude-code"


def _frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path} has no frontmatter"
    _, fm, _body = text.split("---\n", 2)
    return yaml.safe_load(fm)


def test_generated_subagents_are_valid(tmp_path: Path) -> None:
    written, problems = host_mod.generate(out_dir=tmp_path, prompts_dir=host_mod._PROMPTS)
    assert not problems
    assert len(written) == len(host_mod.subagent_roles()) == 9
    known_models = set()
    for tiers in model_config.load_tiers()["hosts"].values():
        for t in tiers.values():
            known_models.add(t.get("model"))
    for name in written:
        fm = _frontmatter(tmp_path / name)
        assert fm["name"] and ":" not in fm["name"]  # valid subagent name
        assert fm["description"]
        assert fm["model"] in known_models and fm["model"] != "unknown"  # never hand-typed
        assert fm["disallowedTools"] == ["Agent"]  # executors/reviewers can't delegate


def test_flagship_unavailable_blocks_researcher(tmp_path: Path, monkeypatch) -> None:  # T63
    tiers = model_config.load_tiers()
    tiers["hosts"]["claude-code"]["flagship"] = {"model": "unknown"}
    monkeypatch.setattr(model_config, "load_tiers", lambda: tiers)

    written, problems = host_mod.generate(out_dir=tmp_path, prompts_dir=host_mod._PROMPTS)
    # researcher/analyst/integration_critic are flagship -> not emitted, reported.
    assert any("researcher" in p for p in problems)
    assert "researcher.md" not in written
    assert not (tmp_path / "researcher.md").exists()
    # strong/fast roles still generate (writer is strong).
    assert "writer.md" in written


def test_committed_agents_match_generator() -> None:
    """The checked-in agents/ are what the generator produces (no hand editing)."""
    agents_dir = _HOST / "agents"
    for role in host_mod.subagent_roles():
        _tier, model_id = model_config.resolve(role, "claude-code")
        path = agents_dir / f"{host_mod._name(role)}.md"
        assert path.read_text(encoding="utf-8") == host_mod._render(
            role, model_id, host_mod._PROMPTS
        )


def _fm_block(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path} has no frontmatter"
    return text.split("---\n", 2)[1].splitlines()


def _field(lines: list[str], key: str) -> str:
    for line in lines:
        if line.startswith(f"{key}:"):
            return line.split(":", 1)[1].strip().strip('"')
    return ""


@pytest.mark.parametrize("sub", ["researcher", "writer", "critic", "summarizer"])
def test_skills_have_valid_frontmatter(sub: str) -> None:
    # Descriptions may contain ':' (valid for the host parser), so check by line.
    lines = _fm_block(_HOST / "skills" / sub / "SKILL.md")
    assert _field(lines, "name") == sub
    assert _field(lines, "description")


@pytest.mark.parametrize(
    "cmd", ["start", "continue", "status", "intake", "research", "draft", "review", "export"]
)
def test_commands_have_description(cmd: str) -> None:
    assert _field(_fm_block(_HOST / "commands" / f"{cmd}.md"), "description")
