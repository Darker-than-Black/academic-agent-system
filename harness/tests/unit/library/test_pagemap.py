"""Page map derivation (02 §12 page_map; T59 both-numberings part)."""

from __future__ import annotations

from research_harness.library.extract import PageText
from research_harness.library.pagemap import build_page_map, pdf_for_printed, printed_for


def _page(n: int, text: str) -> PageText:
    return PageText(pdf_page=n, text=text, sha256="x", extraction_method="t", quality="high")


def test_offset_from_pages_first() -> None:
    pages = [_page(1, "body"), _page(2, "body")]
    pm = build_page_map(pages, first_printed=592)
    assert pm == {"pdf_to_printed_offset": 591}
    assert printed_for(pm, 1) == "592" and printed_for(pm, 2) == "593"
    assert pdf_for_printed(pm, "593") == 2


def test_offset_detected_from_running_footer() -> None:
    pages = [_page(1, "text here\n592"), _page(2, "more text\n593")]
    pm = build_page_map(pages)
    assert pm == {"pdf_to_printed_offset": 591}


def test_varying_offsets_give_explicit() -> None:
    pages = [_page(1, "a\n10"), _page(2, "b\n20")]  # offsets 9 and 18 differ
    pm = build_page_map(pages)
    assert "explicit" in pm
    assert printed_for(pm, 2) == "20"


def test_unknown_when_no_signal() -> None:
    pages = [_page(1, "no numbers"), _page(2, "still none")]
    pm = build_page_map(pages)
    assert pm == {"unknown": True}
    assert printed_for(pm, 1) is None
