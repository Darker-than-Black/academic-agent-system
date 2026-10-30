"""KMU 2010 Ukrainian romanization (T43 transliteration part)."""

from __future__ import annotations

import pytest

from research_harness.core.translit_uk import is_cyrillic, transliterate


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("Гриценко", "Hrytsenko"),
        ("Щербак", "Shcherbak"),
        ("Згурський", "Zghurskyi"),  # зг -> zgh (distinct from ж -> zh)
        ("Жук", "Zhuk"),
        ("Їжак", "Yizhak"),  # initial Ї -> Yi
        ("Яблуня", "Yablunia"),  # initial Я -> Ya; medial я -> ia
        ("Йосип", "Yosyp"),  # initial Й -> Y
        ("Європа", "Yevropa"),  # initial Є -> Ye
        ("Київ", "Kyiv"),
        ("Хо", "Kho"),
        ("Цар", "Tsar"),
        ("Euler", "Euler"),  # Latin passes through
    ],
)
def test_kmu_2010(src: str, expected: str) -> None:
    assert transliterate(src) == expected


def test_apostrophe_and_soft_sign_dropped() -> None:
    assert transliterate("Мар'яна") == "Mariana"
    assert transliterate("Сьомкін") == "Somkin"


def test_is_cyrillic() -> None:
    assert is_cyrillic("Шевченко")
    assert not is_cyrillic("Smith")
