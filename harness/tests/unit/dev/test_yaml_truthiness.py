"""PH-2: guard flags bare YAML booleans where a string is meant."""

from __future__ import annotations

from pathlib import Path

from research_harness_dev.guards import scan_yaml_truthiness


def _write(tmp: Path, name: str, body: str) -> Path:
    d = tmp / "config"
    d.mkdir(exist_ok=True)
    (d / name).write_text(body, encoding="utf-8")
    return d


def test_flags_bare_bool_in_sequence(tmp_path: Path) -> None:
    _write(tmp_path, "intake.yaml", "question:\n  options: [yes, no]\n")
    problems = scan_yaml_truthiness((tmp_path / "config",))
    assert len(problems) == 2
    assert all("bare YAML boolean" in p for p in problems)
    assert any("'yes'" in p for p in problems)
    assert any("'no'" in p for p in problems)


def test_flags_bare_yes_no_on_off_as_scalar_value(tmp_path: Path) -> None:
    _write(tmp_path, "c.yaml", "label: yes\nmode: off\n")
    problems = scan_yaml_truthiness((tmp_path / "config",))
    assert len(problems) == 2


def test_allows_legit_boolean_scalar(tmp_path: Path) -> None:
    # A real boolean mapping value is fine; must not be flagged.
    _write(tmp_path, "budget.yaml", "paid_calls:\n  enabled: true\n  strict: false\n")
    assert scan_yaml_truthiness((tmp_path / "config",)) == []


def test_allows_quoted_tokens(tmp_path: Path) -> None:
    _write(tmp_path, "ok.yaml", "options: ['yes', 'no']\nlabel: \"on\"\n")
    assert scan_yaml_truthiness((tmp_path / "config",)) == []


def test_flags_true_false_only_inside_sequence(tmp_path: Path) -> None:
    _write(tmp_path, "mix.yaml", "choices: [true, false]\nenabled: true\n")
    problems = scan_yaml_truthiness((tmp_path / "config",))
    assert len(problems) == 2  # the two sequence items, not `enabled: true`


def test_missing_dir_is_noop(tmp_path: Path) -> None:
    assert scan_yaml_truthiness((tmp_path / "nope",)) == []
