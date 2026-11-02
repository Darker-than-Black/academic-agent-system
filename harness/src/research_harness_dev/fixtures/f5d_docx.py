"""F5d — a synthetic reviewed ``.docx`` with tracked changes and a comment, for
the M3-09 import tests (docx.md, T46/T58). Output is synthetic (H6): the content
is placeholder Ukrainian, the document is built here by hand as OOXML, and no
real manuscript or review is used.

The document carries the export bookmarks (``unit_<id>`` / ``para_<id>``) so the
importer can map each change. With ``with_unmapped=True`` an extra insertion sits
outside any unit bookmark, to exercise ``import.unmapped_changes`` (T46).
"""

from __future__ import annotations

import zipfile
from pathlib import Path

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml"
    ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/comments.xml"
    ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"/>
</Types>
"""

_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

_RELS = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="{_REL}/officeDocument" Target="word/document.xml"/>
</Relationships>
"""

_DOC_RELS = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="{_REL}/comments" Target="comments.xml"/>
</Relationships>
"""

_COMMENTS = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:comments xmlns:w="{_W}">
  <w:comment w:id="0" w:author="Supervisor" w:date="2026-02-01T10:00:00Z">
    <w:p><w:r><w:t>уточніть джерело</w:t></w:r></w:p>
  </w:comment>
</w:comments>
"""


def _document(unit_id: str, para_ids: tuple[str, str], *, with_unmapped: bool) -> str:
    p1, p2 = para_ids
    unmapped = ""
    if with_unmapped:
        unmapped = (
            '<w:p><w:ins w:id="90" w:author="Editor" w:date="2026-02-01T10:00:00Z">'
            "<w:r><w:t> поза одиницею</w:t></w:r></w:ins></w:p>"
        )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="{_W}">
  <w:body>
    <w:bookmarkStart w:id="1" w:name="unit_{unit_id}"/>
    <w:p>
      <w:bookmarkStart w:id="2" w:name="para_{p1}"/>
      <w:r><w:t>Текст один. </w:t></w:r>
      <w:ins w:id="10" w:author="Editor" w:date="2026-02-01T10:00:00Z">
        <w:r><w:t>додано</w:t></w:r>
      </w:ins>
      <w:bookmarkEnd w:id="2"/>
    </w:p>
    <w:p>
      <w:bookmarkStart w:id="3" w:name="para_{p2}"/>
      <w:commentRangeStart w:id="0"/>
      <w:r><w:t>Текст два.</w:t></w:r>
      <w:del w:id="11" w:author="Editor" w:date="2026-02-01T10:00:00Z">
        <w:r><w:delText> зайве</w:delText></w:r>
      </w:del>
      <w:commentRangeEnd w:id="0"/>
      <w:r><w:commentReference w:id="0"/></w:r>
      <w:bookmarkEnd w:id="3"/>
    </w:p>
    <w:bookmarkEnd w:id="1"/>
    {unmapped}
  </w:body>
</w:document>
"""


def build_f5d(dest: Path) -> Path:
    """`rh-dev fixtures generate F5d` entry: write ``<dest>/reviewed.docx``."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    return build_f5d_docx(dest / "reviewed.docx")


def build_f5d_docx(
    dest: Path,
    *,
    unit_id: str = "U-MPRT2345",
    para_ids: tuple[str, str] = ("PG-MP2345", "PG-MP2346"),
    with_unmapped: bool = False,
) -> Path:
    """Write a synthetic reviewed ``.docx`` to ``dest`` and return its path."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _CONTENT_TYPES)
        zf.writestr("_rels/.rels", _RELS)
        zf.writestr("word/_rels/document.xml.rels", _DOC_RELS)
        zf.writestr("word/document.xml", _document(unit_id, para_ids, with_unmapped=with_unmapped))
        zf.writestr("word/comments.xml", _COMMENTS)
    return dest
