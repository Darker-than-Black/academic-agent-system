"""Generate ``rulepacks/ua-fahove-b/reference.docx`` (M4-12, FR-12).

Documented fixture generator (H6): produces the pandoc reference document that
encodes the Ukrainian cat. «Б» general article format — Times New Roman 14 pt,
1.5 line spacing, first-line indent 1.25 cm, A4 with 2 cm margins, page number
centred in the footer. Pandoc renders article exports against it (presentation
layer, ADR-022).

It starts from pandoc's own default reference document (so the skeleton is always
valid) and patches only the style defaults, the section properties and the footer.
Requires pandoc on PATH to regenerate.

Usage:
    uv run python -m research_harness_dev.make_reference_docx
"""

from __future__ import annotations

import io
import re
import subprocess
import zipfile
from pathlib import Path

_OUT = Path(__file__).resolve().parents[2] / "rulepacks" / "ua-fahove-b" / "reference.docx"

# Twips: 1 cm = 566.93 twips. 2 cm margins, 1.25 cm first-line indent. 14 pt =
# 28 half-points. 1.5 line spacing = 360 (240 = single) with lineRule auto. A4.
_MARGIN = 1134
_INDENT = 709
_SZ = "28"
_LINE = "360"
_A4_W, _A4_H = 11906, 16838

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_FOOTER_REL = "rIdPageFooter"

_NS = (
    'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
)

_FOOTER_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    f"<w:ftr {_NS}>"
    '<w:p><w:pPr><w:jc w:val="center"/></w:pPr>'
    '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
    '<w:r><w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>'
    '<w:r><w:fldChar w:fldCharType="end"/></w:r>'
    "</w:p></w:ftr>"
)


def _patch_doc_defaults(styles: str) -> str:
    """Times New Roman 14 pt, 1.5 spacing, 1.25 cm first-line indent for all text."""
    styles = re.sub(
        r"<w:rPrDefault>\s*<w:rPr>.*?</w:rPr>\s*</w:rPrDefault>",
        "<w:rPrDefault><w:rPr>"
        '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" '
        'w:cs="Times New Roman" w:eastAsia="Times New Roman"/>'
        f'<w:sz w:val="{_SZ}"/><w:szCs w:val="{_SZ}"/>'
        '<w:lang w:val="uk-UA"/>'
        "</w:rPr></w:rPrDefault>",
        styles,
        flags=re.S,
    )
    styles = re.sub(
        r"<w:pPrDefault>\s*<w:pPr>.*?</w:pPr>\s*</w:pPrDefault>",
        "<w:pPrDefault><w:pPr>"
        f'<w:spacing w:after="0" w:line="{_LINE}" w:lineRule="auto"/>'
        f'<w:ind w:firstLine="{_INDENT}"/>'
        "</w:pPr></w:pPrDefault>",
        styles,
        flags=re.S,
    )
    return styles


def _patch_sectpr(doc: str) -> str:
    """A4, 2 cm margins, a default-footer reference for the page number."""
    inner = (
        f'<w:footerReference w:type="default" r:id="{_FOOTER_REL}"/>'
        f'<w:pgSz w:w="{_A4_W}" w:h="{_A4_H}"/>'
        f'<w:pgMar w:top="{_MARGIN}" w:right="{_MARGIN}" w:bottom="{_MARGIN}" '
        f'w:left="{_MARGIN}" w:header="720" w:footer="720" w:gutter="0"/>'
    )
    if "<w:sectPr>" in doc:
        return doc.replace("<w:sectPr>", "<w:sectPr>" + inner, 1)
    if "<w:sectPr " in doc:  # has attributes
        return re.sub(r"(<w:sectPr[^>]*>)", r"\1" + inner, doc, count=1)
    return doc.replace("</w:body>", f"<w:sectPr>{inner}</w:sectPr></w:body>", 1)


def _patch_content_types(ct: str) -> str:
    override = (
        '<Override PartName="/word/footer1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>'
    )
    return ct.replace("</Types>", override + "</Types>", 1)


def _patch_doc_rels(rels: str) -> str:
    rel = f'<Relationship Id="{_FOOTER_REL}" Type="{_R}/footer" Target="footer1.xml"/>'
    return rels.replace("</Relationships>", rel + "</Relationships>", 1)


def build() -> Path:
    base = subprocess.run(  # noqa: S603
        ["pandoc", "--print-default-data-file", "reference.docx"],  # noqa: S607
        capture_output=True,
        check=True,
    ).stdout
    tmp = _OUT.with_suffix(".tmp.docx")
    # Read every part from the base (held in memory), patch, rewrite.
    parts: dict[str, bytes] = {}
    with zipfile.ZipFile(io.BytesIO(base)) as zin:
        for name in zin.namelist():
            parts[name] = zin.read(name)

    parts["word/styles.xml"] = _patch_doc_defaults(parts["word/styles.xml"].decode()).encode()
    parts["word/document.xml"] = _patch_sectpr(parts["word/document.xml"].decode()).encode()
    parts["[Content_Types].xml"] = _patch_content_types(
        parts["[Content_Types].xml"].decode()
    ).encode()
    parts["word/_rels/document.xml.rels"] = _patch_doc_rels(
        parts["word/_rels/document.xml.rels"].decode()
    ).encode()
    parts["word/footer1.xml"] = _FOOTER_XML.encode()

    _OUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in parts.items():
            zout.writestr(name, data)
    tmp.replace(_OUT)
    return _OUT


def main() -> None:
    out = build()
    print(f"wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
