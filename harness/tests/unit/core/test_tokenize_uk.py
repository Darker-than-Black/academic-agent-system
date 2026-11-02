"""P2-2: Ukrainian word normalization — lemma when pymorphy3 is present, a
casefold fallback (unchanged behavior) otherwise."""

from __future__ import annotations

import pytest

from research_harness.core import tokenize_uk


def test_backend_is_one_of_known() -> None:
    assert tokenize_uk.backend() in ("pymorphy3", "regex")


def test_normalize_is_deterministic() -> None:
    assert tokenize_uk.normalize("Дослідження") == tokenize_uk.normalize("Дослідження")


def test_fallback_is_casefold_without_analyzer() -> None:
    if tokenize_uk.backend() != "regex":
        pytest.skip("pymorphy3 installed; the casefold fallback is not active")
    assert tokenize_uk.normalize("Слово") == "слово"
    assert tokenize_uk.normalize("ДОСЛІДЖЕНЬ") == "досліджень"
    # Without the analyzer, inflected forms stay distinct (documents the gap).
    assert tokenize_uk.normalize("дослідження") != tokenize_uk.normalize("досліджень")


@pytest.mark.skipif(
    tokenize_uk.backend() != "pymorphy3", reason="pymorphy3 + dicts-uk not installed"
)
def test_lemmatizes_inflected_forms() -> None:
    n = tokenize_uk.normalize
    assert n("дослідження") == n("досліджень") == n("дослідженню")
    assert n("метод") == n("методи") == n("методів")
