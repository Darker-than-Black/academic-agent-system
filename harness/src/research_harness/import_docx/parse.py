"""Parse a reviewed ``.docx`` for tracked changes and comments, with the unit /
paragraph each one sits in, using the standard library only (zipfile + ElementTree).

OOXML shape (WordprocessingML):

* ``w:ins`` / ``w:moveTo`` — inserted text, in ``w:t`` runs (kept in the accepted
  version); ``w:del`` / ``w:moveFrom`` — deleted text, in ``w:delText`` runs
  (dropped from the accepted version). Each carries ``w:author`` and ``w:date``.
* ``w:bookmarkStart``/``w:bookmarkEnd`` carry the export bookmarks
  (``unit_<id>`` / ``para_<id>``); the innermost open bookmark of each kind at a
  change's position gives its unit and paragraph.
* ``w:commentRangeStart`` marks where a comment attaches; the comment's author,
  date and text live in ``word/comments.xml`` keyed by id.

The parser is deterministic and makes no network or model calls.
"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_CHANGE_TAGS = {"ins", "del", "moveFrom", "moveTo"}
_DOC = "word/document.xml"
_COMMENTS = "word/comments.xml"


def _ln(tag: str) -> str:
    """Local name of a namespaced ElementTree tag (``{ns}p`` -> ``p``)."""
    return tag.rsplit("}", 1)[-1]


def _attr(el: ET.Element, name: str) -> str | None:
    return el.get(f"{{{_W}}}{name}")


@dataclass
class Change:
    """One tracked change or comment, with the unit / paragraph it maps to."""

    type: str  # ins | del | moveFrom | moveTo | comment
    author: str
    date: str
    text: str
    unit_id: str | None
    paragraph_id: str | None
    change_id: str | None


@dataclass
class ParsedImport:
    changes: list[Change] = field(default_factory=list)
    # accepted (tracked changes applied) text per mapped paragraph id.
    accepted: dict[str, str] = field(default_factory=dict)
    count: int = 0  # independent count of raw changes + comments (T46 guard).


def _text_of(el: ET.Element, local: str) -> str:
    """Concatenate every descendant ``w:<local>`` text under ``el``."""
    parts: list[str] = []
    for node in el.iter():
        if _ln(node.tag) == local and node.text:
            parts.append(node.text)
    return "".join(parts)


def _strip(name: str | None, prefix: str) -> str | None:
    if name and name.startswith(prefix):
        return name[len(prefix) :]
    return None


def parse_docx(path: Path) -> ParsedImport:
    with zipfile.ZipFile(path) as zf:
        document = zf.read(_DOC).decode("utf-8")
        comments_xml = zf.read(_COMMENTS).decode("utf-8") if _COMMENTS in zf.namelist() else None

    body = ET.fromstring(document)
    parsed = ParsedImport()
    active: list[tuple[str, str]] = []  # (bookmark id, name) in document order
    accepted: dict[str, list[str]] = {}
    comment_loc: dict[str, tuple[str | None, str | None]] = {}

    def current(prefix: str) -> str | None:
        for _id, name in reversed(active):
            if name.startswith(prefix):
                return name[len(prefix) :]
        return None

    def walk(el: ET.Element) -> None:
        tag = _ln(el.tag)
        if tag == "bookmarkStart":
            active.append((_attr(el, "id") or "", _attr(el, "name") or ""))
            return
        if tag == "bookmarkEnd":
            bid = _attr(el, "id") or ""
            for i in range(len(active) - 1, -1, -1):
                if active[i][0] == bid:
                    active.pop(i)
                    break
            return
        if tag in _CHANGE_TAGS:
            local = "delText" if tag in ("del", "moveFrom") else "t"
            parsed.changes.append(
                Change(
                    type=tag,
                    author=_attr(el, "author") or "unknown",
                    date=_attr(el, "date") or "",
                    text=_text_of(el, local),
                    unit_id=current("unit_"),
                    paragraph_id=current("para_"),
                    change_id=_attr(el, "id"),
                )
            )
            # Recurse so inserted ``w:t`` still lands in the accepted text and
            # inner bookmarks keep tracking; deleted ``w:delText`` is ignored
            # by the ``t`` handler, so it never enters the accepted version.
            for child in el:
                walk(child)
            return
        if tag == "t":
            pid = current("para_")
            if pid is not None:
                accepted.setdefault(pid, []).append(el.text or "")
            return
        if tag == "commentRangeStart":
            cid = _attr(el, "id")
            if cid is not None:
                comment_loc[cid] = (current("unit_"), current("para_"))
            return
        for child in el:
            walk(child)

    walk(body)

    comments = _parse_comments(comments_xml)
    for cid, author, date, text in comments:
        unit_id, paragraph_id = comment_loc.get(cid, (None, None))
        parsed.changes.append(Change("comment", author, date, text, unit_id, paragraph_id, cid))

    parsed.accepted = {pid: "".join(parts) for pid, parts in accepted.items()}
    parsed.count = _raw_count(body) + len(comments)
    return parsed


def _parse_comments(xml: str | None) -> list[tuple[str, str, str, str]]:
    if not xml:
        return []
    out: list[tuple[str, str, str, str]] = []
    for c in ET.fromstring(xml).iter():
        if _ln(c.tag) == "comment":
            out.append(
                (
                    _attr(c, "id") or "",
                    _attr(c, "author") or "unknown",
                    _attr(c, "date") or "",
                    _text_of(c, "t").strip(),
                )
            )
    return out


def _raw_count(body: ET.Element) -> int:
    """Count change elements straight from the tree, independent of the walk,
    so a parser that silently drops one trips ``import.count_mismatch`` (T46)."""
    return sum(1 for el in body.iter() if _ln(el.tag) in _CHANGE_TAGS)
