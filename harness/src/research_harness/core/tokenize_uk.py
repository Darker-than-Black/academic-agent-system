"""Ukrainian-aware word normalization for overlap / shingle comparison (P2-2).

Ukrainian is highly inflected, so comparing surface forms (casefold only) treats
дослідження / досліджень / дослідженню as different tokens and misses reuse. When
the optional morphological analyzer ``pymorphy3`` (+ ``pymorphy3-dicts-uk``) is
installed, :func:`normalize` reduces a word to its lemma so inflected forms
compare equal; without it, it falls back to casefolding, so behavior is exactly
the current regex normalization. The analyzer is a pure-Python NLP library, not
an LLM SDK or a host adapter, so core stays within H5.

The fallback keeps the harness working (and deterministic) when the dependency
is absent; the lemmatizing backend is active only once it is installed.
"""

from __future__ import annotations

import functools


@functools.lru_cache(maxsize=1)
def _analyzer() -> object | None:
    """The pymorphy3 Ukrainian analyzer, or ``None`` if it is not installed."""
    try:
        import pymorphy3  # optional dependency (P2-2)

        return pymorphy3.MorphAnalyzer(lang="uk")
    except Exception:
        # Not installed, or no Ukrainian dictionaries available: fall back.
        return None


def backend() -> str:
    """``"pymorphy3"`` when lemmatizing, ``"regex"`` on the casefold fallback."""
    return "pymorphy3" if _analyzer() is not None else "regex"


@functools.lru_cache(maxsize=100_000)
def normalize(word: str) -> str:
    """Normalize one surface word for comparison: its lemma (lowered) when the
    analyzer is present, else its casefold (identical to the prior behavior)."""
    casefolded = word.casefold()
    analyzer = _analyzer()
    if analyzer is None:
        return casefolded
    try:
        parses = analyzer.parse(word)
    except Exception:
        return casefolded
    if not parses:
        return casefolded
    return str(parses[0].normal_form).casefold()
