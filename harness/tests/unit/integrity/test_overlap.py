"""Overlap check against the author corpus (M3-10, FR-30, T31)."""

from __future__ import annotations

from pathlib import Path

from research_harness.core import tokenize_uk as tok
from research_harness.integrity import overlap as ov

_RUN = "один два три чотири п'ять шість сім вісім дев'ять десять one two three four five"


def _index(text: str, n: int) -> dict:
    return ov._corpus_shingle_index({"corpus-doc.md": text}, n)


def test_shingles_and_tokens_cyrillic() -> None:
    words, spans = ov._tokens("Привіт, Світе! 42")
    # Tokens are normalized via tokenize_uk (lemma when pymorphy3 is installed,
    # casefold otherwise); assert against the active backend, punctuation dropped.
    assert words == [tok.normalize("Привіт"), tok.normalize("Світе"), tok.normalize("42")]
    assert len(spans) == 3
    assert ov.shingles(["a", "b", "c"], 2) == {("a", "b"), ("b", "c")}


def test_long_overlap_matches() -> None:
    idx = _index(_RUN, 3)
    unit = f"prefix words here {_RUN} and a tail that differs completely now"
    matches = ov.find_matches("U-AAAAAAAA", unit, idx, n=3, min_words=10)
    assert len(matches) == 1
    m = matches[0]
    assert m["corpus_doc_id"] == "corpus-doc.md" and m["overlap_words"] >= 15
    assert m["char_end"] > m["char_start"] and m["cited"] is False


def test_short_overlap_below_threshold() -> None:
    idx = _index(_RUN, 3)
    unit = "один два три чотири completely different continuation here and there"
    assert ov.find_matches("U-AAAAAAAA", unit, idx, n=3, min_words=10) == []


def test_case_insensitive_match() -> None:
    idx = _index(_RUN, 3)
    unit = _RUN.upper()
    matches = ov.find_matches("U-AAAAAAAA", unit, idx, n=3, min_words=10)
    assert len(matches) == 1


def test_load_corpus(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("alpha beta", encoding="utf-8")
    (tmp_path / "b.txt").write_text("gamma", encoding="utf-8")
    (tmp_path / "index.json").write_text("{}", encoding="utf-8")  # ignored
    corpus = ov.load_corpus(tmp_path)
    assert set(corpus) == {"a.md", "b.txt"}


def test_run_empty_corpus_is_unknown(tmp_path: Path) -> None:
    report = ov.run(tmp_path, corpus_dir=tmp_path / "missing")
    assert report["result"] == "unknown" and report["matches"] == []
    assert "author corpus is empty" in report["limitations"]
