"""Rule composition, freshness and caps on F5a (02 §8.3–§8.4, T28, T29)."""

from __future__ import annotations

from pathlib import Path

from research_harness.rules.resolver import resolve
from research_harness_dev.fixtures.f5a_rules import build_f5a, load_f5a


def _stack(tmp_path: Path):
    build_f5a(tmp_path / "f5a")
    return resolve(load_f5a(tmp_path / "f5a"), at="2026-10-29")


def _effective(stack, key: str) -> list[dict]:
    return [r for r in stack.rules if r["key"] == key and r["effective"]]


def _findings(stack, check_id: str, key: str | None = None) -> list[dict]:
    return [
        f for f in stack.findings if f["check_id"] == check_id and (key is None or f["key"] == key)
    ]


def test_structure_comes_from_highest_journal_layer(tmp_path: Path) -> None:
    stack = _stack(tmp_path)
    eff = _effective(stack, "structure.sections")
    assert len(eff) == 1 and eff[0]["rule_id"] == "FJ-SECTIONS"  # layer 5 beats layer 4
    overridden = [r for r in stack.rules if r["rule_id"] == "FI-SECTIONS"][0]
    assert overridden["effective"] is False


def test_integrity_strictest_value_highest_severity(tmp_path: Path) -> None:
    stack = _stack(tmp_path)
    eff = _effective(stack, "integrity.selfplag")
    assert eff and all(r["effective_value"] == 0.9 for r in eff)  # max of 0.9 / 0.8
    assert all(r["effective_severity"] == "blocker" for r in eff)  # highest severity


def test_same_layer_conflict_and_incomparable_are_blockers(tmp_path: Path) -> None:
    stack = _stack(tmp_path)
    assert _findings(stack, "rules.conflict", "format.layout")[0]["severity"] == "blocker"
    inc = _findings(stack, "rules.conflict", "integrity.ratio")
    assert inc and inc[0]["severity"] == "blocker"
    assert all(f["at"] == "A0" for f in _findings(stack, "rules.conflict"))


def test_core_override_attempt_is_major(tmp_path: Path) -> None:
    stack = _stack(tmp_path)
    f = _findings(stack, "rules.core_override_attempt", "integrity.no_invented_evidence")
    assert f and f[0]["severity"] == "major"
    core_eff = _effective(stack, "integrity.no_invented_evidence")
    assert core_eff and core_eff[0]["rule_id"] == "FC-NOINVENT"
    assert [r for r in stack.rules if r["rule_id"] == "FO-OVERRIDE"][0]["effective"] is False


def test_expired_rule_blocks_verified_export(tmp_path: Path) -> None:
    stack = _stack(tmp_path)
    entry = [r for r in stack.rules if r["rule_id"] == "FE-MINREFS"][0]
    assert entry["freshness"] == "expired"
    assert stack.export_blocked() is True
    assert _findings(stack, "rules.expired")


def test_secondary_blocker_capped_at_major(tmp_path: Path) -> None:
    stack = _stack(tmp_path)
    eff = _effective(stack, "integrity.secondary_demo")
    assert eff and eff[0]["effective_severity"] == "major"
