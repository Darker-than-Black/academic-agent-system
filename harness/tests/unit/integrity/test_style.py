"""Style profile + stylization invariant check (M3-13, FR-19/FR-19a, T19)."""

from __future__ import annotations

from research_harness.integrity import errors as errors_mod
from research_harness.integrity import style as s


def test_invariants_preserved_on_reword() -> None:
    before = "Ми виявили, що 42% зразків відповідають критерію [[cite:smith2020]]."
    after = "Було виявлено, що 42% зразків відповідають критерію [[cite:smith2020]]."
    assert s.invariant_check(before, after) == []


def test_number_change_blocks() -> None:
    f = s.invariant_check("частка 42%", "частка 43%")
    assert f and f[0]["check_id"] == "integrity.style_invariants"
    assert f[0]["severity"] == "blocker"


def test_citation_drop_blocks() -> None:
    f = s.invariant_check("as shown [[cite:a1]] and [[cite:b2]]", "as shown [[cite:a1]]")
    assert any(x["observed"] == "citations" for x in f)


def test_qualifier_change_blocks() -> None:
    f = s.invariant_check("приблизно 10 випадків", "10 випадків")
    assert any(x["observed"] == "qualifiers" for x in f)


def test_build_profile_voice_and_features() -> None:
    catalog = errors_mod.load_catalog()
    texts = ["Ми показали ефект. Ми вважаємо це важливим. Однак є виняток."]
    prof = s.build_profile(texts, "uk", voice_markers=catalog["voice_markers"])
    assert prof["lang"] == "uk" and prof["version"] == 1
    assert prof["features"]["voice"] == "we"
    assert prof["features"]["sentence_length"] > 0
    assert "однак" in prof["features"]["connectives"]
