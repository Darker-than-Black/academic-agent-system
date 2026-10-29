"""Path and name handling (01 §4, 02 §1.5; NFR-02, NFR-14).

- Names created by ``rh`` are NFC; lookups compare NFC (macOS may return NFD).
- Forbidden characters are removed; leading/trailing spaces and trailing dots
  stripped; a title is trimmed to 60 chars at a word boundary (the ID suffix is
  never trimmed — that belongs to the caller that joins title and ID).
- Stored paths are relative, POSIX, NFC; absolute paths and ``..`` are rejected.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path, PurePosixPath

_WS_RUN = re.compile(r"\s+")

# 01 §4: forbidden filename characters.
FORBIDDEN_CHARS = set(':?«»/\\*|<>"')
TITLE_LIMIT = 60


def nfc(text: str) -> str:
    """Unicode NFC normalization."""
    return unicodedata.normalize("NFC", text)


def sanitize_name(name: str) -> str:
    """Remove forbidden characters; collapse whitespace runs; strip edge spaces
    and trailing dots; NFC.

    01 §4 lists only character removal and edge stripping. Whitespace runs are
    collapsed to a single space so that a separator removed from between words
    (``«тест» / ?`` → ``тест``) does not leave a double space in the name.
    """
    cleaned = "".join(ch for ch in name if ch not in FORBIDDEN_CHARS)
    cleaned = _WS_RUN.sub(" ", cleaned).strip()
    cleaned = cleaned.rstrip(".").strip()
    return nfc(cleaned)


def trim_title(title: str, limit: int = TITLE_LIMIT) -> str:
    """Trim ``title`` to ``limit`` chars at a word boundary where possible."""
    title = title.strip()
    if len(title) <= limit:
        return title
    window = title[:limit]
    if " " in window:
        trimmed = window[: window.rfind(" ")].strip()
        if trimmed:
            return trimmed
    return window.strip()


def sanitize_title(title: str, limit: int = TITLE_LIMIT) -> str:
    """Sanitize then trim a title for use as the human part of a folder name."""
    return trim_title(sanitize_name(title), limit)


def is_safe_relative(path: str) -> bool:
    """True if ``path`` is relative, POSIX, and contains no ``..`` segment."""
    if not path or path.startswith("/"):
        return False
    pure = PurePosixPath(path)
    if pure.is_absolute():
        return False
    return not any(part == ".." for part in pure.parts)


def validate_relative_path(path: str) -> str:
    """Return the NFC POSIX form of a safe relative path; raise otherwise."""
    normalized = nfc(path.replace("\\", "/"))
    if not is_safe_relative(normalized):
        raise ValueError(f"unsafe or non-relative path: {path!r}")
    return str(PurePosixPath(normalized))


def nfc_lookup(directory: str | Path, name: str) -> Path | None:
    """Find a child of ``directory`` whose name equals ``name`` under NFC."""
    directory = Path(directory)
    if not directory.is_dir():
        return None
    target = nfc(name)
    direct = directory / name
    if direct.exists():
        return direct
    for child in directory.iterdir():
        if nfc(child.name) == target:
            return child
    return None
