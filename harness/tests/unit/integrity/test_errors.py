"""Typical-errors catalogue, check and profile (M3-13, FR-51, T56)."""

from __future__ import annotations

from pathlib import Path

import pytest

from research_harness.integrity import errors as e


def test_calque_chosen_vs_unchosen() -> None:
    text = "Результат в залежності від умов."
    chosen = e.check_text(text, chosen={"calque_bureaucratese"})
    assert chosen and chosen[0]["check_id"] == "integrity.chosen_error"
    assert chosen[0]["severity"] == "major"
    unchosen = e.check_text(text, chosen=set())
    assert unchosen[0]["check_id"] == "integrity.error" and unchosen[0]["severity"] == "minor"


def test_voice_mixing_flagged() -> None:
    text = "Я показав ефект. Ми вважаємо це важливим."
    f = e.check_text(text, chosen={"voice_person"})
    assert any("voice/person mixing" in x["reason"] for x in f)


def test_clean_text_no_findings() -> None:
    assert e.check_text("Було встановлено, що зразок стабільний.", chosen=set()) == []


def test_check_never_edits_input() -> None:
    text = "в якості прикладу"
    before = text
    e.check_text(text, chosen={"calque_bureaucratese"})
    assert text == before  # T56: reporting never mutates the text


def test_choose_and_unknown(tmp_path: Path) -> None:
    prof = e.choose(tmp_path, ["voice_person", "calque_bureaucratese"], voice="impersonal")
    assert e.chosen_ids(prof) == {"voice_person", "calque_bureaucratese"}
    assert prof["version"] == 2  # default 1 -> bumped
    with pytest.raises(ValueError):
        e.choose(tmp_path, ["not_a_category"])


def test_catalog_has_categories() -> None:
    cat = e.load_catalog()
    ids = {c["id"] for c in cat["categories"]}
    assert {"voice_person", "calque_bureaucratese", "terminology"} <= ids
