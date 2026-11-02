"""Codex critic engine selection and gating (M3-17, review.md, FR-58, T64).

Off by default; gated by config, intake Q3b and the Codex binary. These tests
never enable a paid API (H9) — they exercise the gating and fallback only."""

from __future__ import annotations

from pathlib import Path

from research_harness.intake import answers as answers_mod
from research_harness.review import engine


def test_claude_engine_is_always_ok(tmp_path: Path) -> None:
    r = engine.resolve_engine(tmp_path, "claude")
    assert r["engine"] == "claude" and r["engine_status"] == engine.OK


def test_codex_disabled_by_default(tmp_path: Path) -> None:
    # The shipped config has codex_critic.enabled: false.
    assert engine.codex_enabled() is False
    r = engine.resolve_engine(tmp_path, "codex")
    assert r["engine_status"] == engine.DISABLED and r["requested"] == "codex"


def test_codex_blocked_without_q3b(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(engine, "codex_enabled", lambda: True)
    r = engine.resolve_engine(tmp_path, "codex")  # no Q3b answer recorded
    assert r["engine_status"] == engine.BLOCKED and r["engine"] == "claude"


def test_codex_unavailable_falls_back(tmp_path: Path, monkeypatch) -> None:
    answers_mod.record(tmp_path, "Q3b", "yes")
    monkeypatch.setattr(engine, "codex_enabled", lambda: True)
    monkeypatch.setattr(engine, "codex_available", lambda: False)
    r = engine.resolve_engine(tmp_path, "codex")
    assert r["engine_status"] == engine.UNAVAILABLE and r["engine"] == "claude"


def test_codex_ok_when_enabled_permitted_available(tmp_path: Path, monkeypatch) -> None:
    answers_mod.record(tmp_path, "Q3b", "yes")
    monkeypatch.setattr(engine, "codex_enabled", lambda: True)
    monkeypatch.setattr(engine, "codex_available", lambda: True)
    r = engine.resolve_engine(tmp_path, "codex")
    assert r["engine_status"] == engine.OK and r["engine"] == "codex"


def test_q3b_permission_reading(tmp_path: Path) -> None:
    assert engine.q3b_permits(tmp_path) is False
    answers_mod.record(tmp_path, "Q3b", "yes")
    assert engine.q3b_permits(tmp_path) is True
    answers_mod.record(tmp_path, "Q3b", "no")
    assert engine.q3b_permits(tmp_path) is False


def test_prepare_records_engine_and_fresh_context(tmp_path: Path) -> None:
    from research_harness.review import handoff

    rec = handoff.prepare(tmp_path, "article", engine="codex")
    assert rec["engine"] == "codex" and rec["engine_status"] == engine.DISABLED
    assert rec["fresh_context"] is True
    ok = handoff.prepare(tmp_path, "article", engine="claude")
    assert ok["engine"] == "claude" and ok["engine_status"] == engine.OK


def test_codex_argv_is_noninteractive_json(tmp_path: Path) -> None:
    argv = engine.build_argv(tmp_path, "review this")
    assert argv[:3] == ["codex", "exec", "--json"]
    assert "--cd" in argv and argv[-1] == "review this"
