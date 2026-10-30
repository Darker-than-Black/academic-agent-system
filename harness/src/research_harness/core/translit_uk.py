"""Ukrainian romanization (KMU 2010), for author-name transliteration (M2-01).

The table lives in ``translit_uk.yaml`` (data, H10). This module applies it:
word-boundary aware (the Є/Ї/Й/Ю/Я initial forms and the ``зг``→``zgh`` digraph),
case-preserving, leaving non-Cyrillic characters untouched.

Used by the source registry to transliterate Cyrillic author names and to make
dedup title matching transliteration-insensitive (02 §12; FR-43, T43).
"""

from __future__ import annotations

from functools import cache
from importlib.resources import files

import yaml


@cache
def _table() -> dict[str, object]:
    raw = files(__package__).joinpath("translit_uk.yaml").read_text(encoding="utf-8")
    return yaml.safe_load(raw) or {}


def _is_word_char(ch: str) -> bool:
    return ch.isalpha()


def _apply_case(src: str, latin: str) -> str:
    """Carry the source letter's case onto its (possibly multi-char) Latin form."""
    if not latin or not src.isupper():
        return latin
    # Uppercase source: title-case a digraph (Kh, Shch), upper a single char.
    if len(latin) == 1:
        return latin.upper()
    return latin[0].upper() + latin[1:]


def transliterate(text: str) -> str:
    """Romanize Ukrainian ``text`` per KMU 2010; pass other characters through."""
    table = _table()
    base: dict[str, str] = table["base"]  # type: ignore[assignment]
    initial: dict[str, str] = table["initial"]  # type: ignore[assignment]
    digraphs: dict[str, str] = table["digraphs"]  # type: ignore[assignment]
    drop: set[str] = set(table.get("drop", []))  # type: ignore[arg-type]

    out: list[str] = []
    i = 0
    n = len(text)
    prev_was_letter = False  # a dropped apostrophe/soft sign does NOT start a word
    while i < n:
        ch = text[i]
        if ch in drop:
            i += 1
            continue
        low = ch.lower()
        at_word_start = not prev_was_letter

        # Digraph (e.g. зг -> zgh) takes priority.
        if i + 1 < n:
            pair = (ch + text[i + 1]).lower()
            if pair in digraphs:
                out.append(_apply_case(ch, digraphs[pair]))
                i += 2
                prev_was_letter = True
                continue

        if low in base:
            latin = initial[low] if at_word_start and low in initial else base[low]
            out.append(_apply_case(ch, latin))
            i += 1
            prev_was_letter = True
            continue

        out.append(ch)
        i += 1
        prev_was_letter = _is_word_char(ch)
    return "".join(out)


def is_cyrillic(text: str) -> bool:
    """True if ``text`` contains at least one Cyrillic letter."""
    return any("Ѐ" <= ch <= "ӿ" for ch in text)
