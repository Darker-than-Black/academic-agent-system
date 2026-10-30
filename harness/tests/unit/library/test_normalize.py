"""Quote-check normalization (04-modules invariant 8)."""

from __future__ import annotations

from research_harness.library.normalize import contains, normalize


def test_whitespace_collapsed() -> None:
    assert normalize("a   b\n\tc") == "a b c"


def test_soft_hyphen_removed() -> None:
    assert normalize("спів­праця") == "співпраця"


def test_line_break_hyphenation_joined() -> None:
    assert normalize("оціню-\nвання") == "оцінювання"
    assert normalize("assess-\n  ment") == "assessment"


def test_typographic_quotes_and_apostrophes_unified() -> None:
    assert normalize("«Текст»") == '"Текст"'
    assert normalize("“quote”") == '"quote"'
    # Ukrainian apostrophe variants all fold to '
    assert normalize("Мар’яна") == normalize("Марʼяна") == "Мар'яна"


def test_contains_after_normalization() -> None:
    page = "Формувальне   оці-\nнювання «підвищує» успішність."
    assert contains(page, 'Формувальне оцінювання "підвищує" успішність.')
    assert not contains(page, "Формувальне оцінювання знижує успішність.")
