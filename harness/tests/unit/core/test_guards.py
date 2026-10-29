"""Static guard tests (M1-02: H5/T15 imports, i18n, adoption, envelope, lock)."""

from __future__ import annotations

from pathlib import Path

from research_harness_dev import guards

REPO_ROOT = Path(__file__).resolve().parents[4]
HARNESS = REPO_ROOT / "harness"
PACKAGE_ROOT = HARNESS / "src" / "research_harness"


def test_real_package_has_no_forbidden_imports() -> None:
    assert guards.scan_forbidden_imports(PACKAGE_ROOT) == []


def test_forbidden_import_detected(tmp_path: Path) -> None:
    (tmp_path / "bad.py").write_text("import anthropic\n", encoding="utf-8")
    violations = guards.scan_forbidden_imports(tmp_path)
    assert any("anthropic" in v for v in violations)


def test_forbidden_from_import_and_prefix(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("from langchain.chains import X\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("import google.generativeai as g\n", encoding="utf-8")
    (tmp_path / "c.py").write_text("import research_harness_dev\n", encoding="utf-8")
    violations = guards.scan_forbidden_imports(tmp_path)
    assert len(violations) == 3


def test_google_other_submodule_allowed(tmp_path: Path) -> None:
    (tmp_path / "ok.py").write_text("import google.protobuf\n", encoding="utf-8")
    assert guards.scan_forbidden_imports(tmp_path) == []


def test_real_catalogs_symmetric() -> None:
    assert guards.check_i18n_catalogs(PACKAGE_ROOT / "i18n") == []


def test_i18n_missing_key_detected(tmp_path: Path) -> None:
    (tmp_path / "uk.yaml").write_text("a: А\nb: Б\n", encoding="utf-8")
    (tmp_path / "en.yaml").write_text("a: A\n", encoding="utf-8")
    problems = guards.check_i18n_catalogs(tmp_path)
    assert any("'b'" in p for p in problems)


def test_envelope_literal_detected(tmp_path: Path) -> None:
    code = "build(message='hello')\nobj.why = 'bad'\n"
    (tmp_path / "x.py").write_text(code, encoding="utf-8")
    problems = guards.scan_envelope_literals(tmp_path)
    assert len(problems) == 2


def test_real_package_has_no_envelope_literals() -> None:
    assert guards.scan_envelope_literals(PACKAGE_ROOT) == []


def test_lockfile_guard_flags_forbidden(tmp_path: Path) -> None:
    lock = tmp_path / "uv.lock"
    lock.write_text('[[package]]\nname = "pymupdf"\nversion = "1.0"\n', encoding="utf-8")
    assert guards.scan_lockfile(lock) == ["pymupdf"]


def test_real_lockfile_clean() -> None:
    assert guards.scan_lockfile(HARNESS / "uv.lock") == []


def test_adoption_records_valid() -> None:
    assert guards.validate_adoptions(REPO_ROOT) == []
