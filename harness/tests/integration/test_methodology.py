"""Review methodology (M4-17): corpus reproducibility record, deficits, render."""

from __future__ import annotations

from pathlib import Path

import pytest

from research_harness.methodology import record as record_mod
from research_harness.schemas import validate
from research_harness.sources import registry
from research_harness.workspace.objects import create_object
from research_harness.workspace.workspace import Workspace

_COMPLETE = {
    "schema_version": "0.2",
    "selection_criteria": {
        "inclusion": ["peer-reviewed", "2015–2025", "gamification + inclusion"],
        "exclusion": ["non-English/Ukrainian", "no empirical data"],
    },
    "search_log": {
        "databases": [
            {
                "name": "Scopus",
                "query": "gamification AND inclusion",
                "date": "2026-10-01",
                "found": 142,
            }
        ],
        "counts": {"found": 142, "screened": 40, "included": 9, "excluded": 31},
        "exclusions": [{"reason": "off-topic", "count": 31}],
    },
}


def _object(tmp_path: Path):
    ws = Workspace.init(tmp_path / "Projects")
    _oid, folder = create_object(ws, title="Огляд", kind="article", document_kind="article")
    return folder


def _identified_source(folder: Path) -> None:
    registry.add_records(
        folder,
        [
            {
                "author": "Smith, J.",
                "title": "On inclusion",
                "year": "2020",
                "metadata_status": "matched",
            }
        ],
    )


def test_empty_object_reports_search_log_and_criteria_missing(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    checks = {f["check_id"] for f in record_mod.deficits(folder)}
    assert "methodology.search_log_missing" in checks
    assert "methodology.selection_criteria_missing" in checks


def test_unidentified_source_is_flagged(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    registry.add_records(folder, [{"title": "", "metadata_status": "unresolved"}])
    checks = [f["check_id"] for f in record_mod.deficits(folder)]
    assert "methodology.corpus_unidentified" in checks


def test_complete_methodology_and_identified_corpus_passes(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    record_mod.save(folder, dict(_COMPLETE))
    _identified_source(folder)
    assert record_mod.deficits(folder) == []


def test_methods_markdown_renders_table_and_search(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    record_mod.save(folder, dict(_COMPLETE))
    _identified_source(folder)
    md = record_mod.methods_markdown(folder)
    assert "## Критерії відбору" in md
    assert "## Стратегія пошуку" in md
    assert "Scopus" in md and "знайдено: 142" in md
    assert "## Включені джерела" in md
    assert "| 1 | Smith J. (2020) On inclusion |" in md


def test_unknown_count_renders_as_unknown(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    record_mod.save(
        folder,
        {
            "schema_version": "0.2",
            "selection_criteria": {"inclusion": ["x"]},
            "search_log": {
                "counts": {"found": None, "screened": None, "included": 9, "excluded": None}
            },
        },
    )
    md = record_mod.methods_markdown(folder)
    assert "знайдено невідомо" in md
    assert "включено 9" in md


def test_save_rejects_invalid_record(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    with pytest.raises(ValueError):
        record_mod.save(folder, {"schema_version": "0.2", "bogus": True})


def test_schema_is_registered() -> None:
    assert validate("review-methodology", _COMPLETE) == []
