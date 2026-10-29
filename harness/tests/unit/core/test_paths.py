"""Path and name handling tests (01 §4, 02 §1.5)."""

from __future__ import annotations

import unicodedata
from pathlib import Path

import pytest

from research_harness.core import paths


def test_nfd_input_produces_nfc_name() -> None:
    # "Новий" contains "й" (U+0439), which decomposes under NFD.
    nfc_name = "Новий розділ"
    nfd = unicodedata.normalize("NFD", nfc_name)
    assert nfd != nfc_name  # decomposed form differs byte-wise
    assert paths.sanitize_name(nfd) == unicodedata.normalize("NFC", nfc_name)


def test_sanitize_removes_forbidden_chars() -> None:
    # Назва: «тест» / ?  → forbidden chars removed, edges trimmed, NFC.
    assert paths.sanitize_name("Назва: «тест» / ?") == "Назва тест"


def test_sanitize_strips_trailing_dots_and_spaces() -> None:
    assert paths.sanitize_name("  Розділ 1.  ") == "Розділ 1"


def test_trim_title_at_word_boundary() -> None:
    title = "A B C D E F G H I J K L M N O P Q R S T U V W X Y Z extra words here padding"
    trimmed = paths.trim_title(title, limit=60)
    assert len(trimmed) <= 60
    assert not trimmed.endswith(" ")
    assert title.startswith(trimmed)


def test_trim_title_short_unchanged() -> None:
    assert paths.trim_title("Вступ", 60) == "Вступ"


def test_cyrillic_title_sanitize_title() -> None:
    assert paths.sanitize_title("Вступ до аналізу") == "Вступ до аналізу"


@pytest.mark.parametrize("bad", ["/etc/passwd", "../secret", "a/../b", "/"])
def test_reject_absolute_and_dotdot(bad: str) -> None:
    with pytest.raises(ValueError):
        paths.validate_relative_path(bad)


def test_accept_relative_posix() -> None:
    assert paths.validate_relative_path("materials/inbox/notes.txt") == "materials/inbox/notes.txt"


def test_backslash_normalized_then_validated() -> None:
    assert paths.validate_relative_path("materials\\inbox\\a.txt") == "materials/inbox/a.txt"


def test_nfc_lookup_matches_nfd_on_disk(tmp_path: Path) -> None:
    nfd_name = unicodedata.normalize("NFD", "Вступ")
    (tmp_path / nfd_name).mkdir()
    found = paths.nfc_lookup(tmp_path, "Вступ")
    assert found is not None
