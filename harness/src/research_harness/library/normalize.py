"""Text normalization for the deterministic quote check (04-modules invariant 8).

A quote passes only if, after the SAME normalization of both the cited excerpt
and the page text, the excerpt is a substring of the page. Normalization is
conservative and reversible in meaning: Unicode NFC; soft hyphens removed;
line-end hyphenation joined; typographic quotes and Ukrainian apostrophe
variants unified; whitespace collapsed.
"""

from __future__ import annotations

import re
import unicodedata

_SOFT_HYPHEN = "­"
# Hyphen (ordinary or soft) at a line end splitting a word -> join the halves.
_HYPHEN_LINEBREAK = re.compile(r"(\w)[-­]\n[ \t]*(\w)")
_WHITESPACE = re.compile(r"\s+")

# Typographic double quotes -> ", single quotes/apostrophes -> '.
_DOUBLE_QUOTES = "“”„‟«»‹›"  # “ ” „ ‟ « » ‹ ›
_APOSTROPHES = "‘’‚‛ʼ′`´"  # ‘ ’ ‚ ‛ ʼ ′ ` ´
_QUOTE_MAP = {ord(c): '"' for c in _DOUBLE_QUOTES} | {ord(c): "'" for c in _APOSTROPHES}


def normalize(text: str) -> str:
    """Normalize ``text`` for quote matching (idempotent)."""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = _HYPHEN_LINEBREAK.sub(r"\1\2", text)
    text = text.replace(_SOFT_HYPHEN, "")
    text = text.translate(_QUOTE_MAP)
    text = _WHITESPACE.sub(" ", text)
    return text.strip()


def contains(haystack: str, needle: str) -> bool:
    """True if the normalized ``needle`` is a substring of the normalized ``haystack``."""
    n = normalize(needle)
    return bool(n) and n in normalize(haystack)
