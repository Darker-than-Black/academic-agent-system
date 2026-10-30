"""Per-page PDF text extraction (pypdf first, pdfminer.six fallback for layout).

Each page is stored in ``sources/pagetext/<S-id>.jsonl`` (gitignored, derived
from foreign text) as ``{pdf_page, printed_page, text, sha256, extraction_method,
quality}``. ``quality`` gates the quote check: a ``low`` page yields
``unverifiable`` rather than ``not_found`` (04-modules open point [P]).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

QUALITY_LOW = "low"
QUALITY_MEDIUM = "medium"
QUALITY_HIGH = "high"


@dataclass
class PageText:
    pdf_page: int  # 1-based
    text: str
    sha256: str
    extraction_method: str
    quality: str
    printed_page: str | None = None


def _quality(text: str) -> str:
    stripped = text.strip()
    if len(stripped) < 20:
        return QUALITY_LOW
    letters = sum(1 for c in stripped if c.isalpha())
    if letters / max(len(stripped), 1) < 0.30:
        return QUALITY_LOW
    return QUALITY_MEDIUM if len(stripped) < 100 else QUALITY_HIGH


def _pypdf_pages(pdf_path: Path) -> list[str]:
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    return [(page.extract_text() or "") for page in reader.pages]


def _pdfminer_page(pdf_path: Path, index0: int) -> str:
    from pdfminer.high_level import extract_text

    try:
        return extract_text(str(pdf_path), page_numbers=[index0]) or ""
    except Exception:  # noqa: BLE001 - fallback best effort
        return ""


def extract_pages(pdf_path: Path) -> list[PageText]:
    """Extract every page; retry low-quality pages with the layout engine."""
    pages: list[PageText] = []
    raw_pages = _pypdf_pages(pdf_path)
    for i, text in enumerate(raw_pages):
        method = "pypdf"
        quality = _quality(text)
        if quality == QUALITY_LOW:
            alt = _pdfminer_page(pdf_path, i)
            if _quality(alt) != QUALITY_LOW:
                text, method, quality = alt, "pdfminer", _quality(alt)
        pages.append(
            PageText(
                pdf_page=i + 1,
                text=text,
                sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                extraction_method=method,
                quality=quality,
            )
        )
    return pages


def pagetext_path(root: Path, source_id: str) -> Path:
    return root / "sources" / "pagetext" / f"{source_id}.jsonl"


def write_pagetext(root: Path, source_id: str, pages: list[PageText]) -> Path:
    path = pagetext_path(root, source_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(
            {
                "pdf_page": p.pdf_page,
                "printed_page": p.printed_page,
                "text": p.text,
                "sha256": p.sha256,
                "extraction_method": p.extraction_method,
                "quality": p.quality,
            },
            ensure_ascii=False,
        )
        for p in pages
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def load_pagetext(root: Path, source_id: str) -> list[PageText]:
    path = pagetext_path(root, source_id)
    if not path.is_file():
        return []
    out: list[PageText] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        out.append(
            PageText(
                pdf_page=d["pdf_page"],
                text=d["text"],
                sha256=d["sha256"],
                extraction_method=d["extraction_method"],
                quality=d["quality"],
                printed_page=d.get("printed_page"),
            )
        )
    return out


@dataclass
class ExtractionResult:
    source_id: str
    pages: list[PageText] = field(default_factory=list)
