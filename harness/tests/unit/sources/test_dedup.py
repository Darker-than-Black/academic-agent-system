"""Source dedup: link (not merge), transliteration-insensitive title match (T43)."""

from __future__ import annotations

from research_harness.sources.dedup import link_duplicates


def test_doi_duplicate_linked_not_merged() -> None:
    recs = [
        {"id": "S-0001", "doi": "10.1234/x", "title": "A"},
        {"id": "S-0002", "doi": "10.1234/x", "title": "A (preprint)"},
    ]
    link_duplicates(recs)
    assert "duplicate_of" not in recs[0]
    assert recs[1]["duplicate_of"] == "S-0001"  # both kept, second linked


def test_transliteration_insensitive_title_match() -> None:
    recs = [
        {
            "id": "S-0001",
            "title": "Формувальне оцінювання",
            "authors": [{"family": "Шевченко"}],
            "year": 2024,
        },
        {
            "id": "S-0002",
            "title": "Formuvalne otsiniuvannia",
            "authors": [{"family": "Shevchenko"}],
            "year": 2024,
        },
    ]
    link_duplicates(recs)
    assert recs[1]["duplicate_of"] == "S-0001"


def test_distinct_sources_not_linked() -> None:
    recs = [
        {"id": "S-0001", "title": "Alpha", "authors": [{"family": "A"}], "year": 2020},
        {"id": "S-0002", "title": "Beta", "authors": [{"family": "B"}], "year": 2021},
    ]
    link_duplicates(recs)
    assert "duplicate_of" not in recs[1]
