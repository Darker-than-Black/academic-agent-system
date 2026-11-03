"""Source language / jurisdiction check (M4-13): forbidden ru/by sources."""

from __future__ import annotations

from pathlib import Path

from research_harness.integrity import source_origin
from research_harness.rules.loader import lint_pack
from research_harness.sources import registry
from research_harness.workspace.objects import create_object
from research_harness.workspace.workspace import Workspace

_PACK = Path(__file__).parents[2] / "rulepacks" / "ua-fahove-b"


def _object(tmp_path: Path):
    ws = Workspace.init(tmp_path / "Projects")
    _oid, folder = create_object(ws, title="Джерела", kind="article", document_kind="article")
    return folder


def _by_check(findings):
    return {f["check_id"]: f for f in findings}


def test_russian_language_source_is_blocker(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    registry.add_records(
        folder, [{"title": "Статья", "language": "ru", "publication_country": "UA"}]
    )
    findings = source_origin.origin_findings(folder)
    f = _by_check(findings)
    assert "integrity.source_language_forbidden" in f
    assert f["integrity.source_language_forbidden"]["severity"] == "blocker"


def test_russian_jurisdiction_source_is_blocker(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    # English-language but published in the Russian Federation -> forbidden.
    registry.add_records(
        folder, [{"title": "Paper", "language": "en", "publication_country": "RU"}]
    )
    findings = source_origin.origin_findings(folder)
    f = _by_check(findings)
    assert "integrity.source_jurisdiction_forbidden" in f
    assert f["integrity.source_jurisdiction_forbidden"]["severity"] == "blocker"


def test_belarus_jurisdiction_source_is_blocker(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    registry.add_records(
        folder, [{"title": "Paper", "language": "en", "publication_country": "BY"}]
    )
    assert "integrity.source_jurisdiction_forbidden" in _by_check(
        source_origin.origin_findings(folder)
    )


def test_unknown_language_source_is_major(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    registry.add_records(folder, [{"title": "No language given"}])  # no language field
    f = _by_check(source_origin.origin_findings(folder))
    assert "integrity.source_origin_unknown" in f
    assert f["integrity.source_origin_unknown"]["severity"] == "major"


def test_clean_english_source_has_no_finding(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    registry.add_records(
        folder, [{"title": "Clean", "language": "en", "publication_country": "GB"}]
    )
    assert source_origin.origin_findings(folder) == []


def test_ukrainian_source_has_no_finding(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    registry.add_records(
        folder, [{"title": "Чисте", "language": "uk", "publication_country": "UA"}]
    )
    assert source_origin.origin_findings(folder) == []


def test_sources_rulepack_lints_clean() -> None:
    assert lint_pack(_PACK) == []
