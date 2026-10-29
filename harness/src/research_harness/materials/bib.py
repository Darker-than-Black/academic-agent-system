"""Minimal, dependency-free BibTeX parsing (02 §9.2).

Only the fields needed for registration and dedup: key, DOI, title, author,
year, url. Brace-aware scanner so compact and multi-line entries both parse.
Deterministic and offline; full parsing / metadata lookup is M2.
"""

from __future__ import annotations

from typing import Any

_WANT = {"doi", "title", "author", "year", "url"}


def _entry_bodies(text: str) -> list[tuple[str, str]]:
    """Return (entry_type, body) for each ``@type{ body }`` with balanced braces."""
    out: list[tuple[str, str]] = []
    i = 0
    n = len(text)
    while i < n:
        if text[i] != "@":
            i += 1
            continue
        j = i + 1
        while j < n and text[j] not in "{(":
            j += 1
        if j >= n:
            break
        etype = text[i + 1 : j].strip()
        depth = 0
        k = j
        while k < n:
            if text[k] in "{(":
                depth += 1
            elif text[k] in "})":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        out.append((etype, text[j + 1 : k]))
        i = k + 1
    return out


def _split_top(body: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    in_quote = False
    for ch in body:
        if ch == '"' and depth == 0:
            in_quote = not in_quote
        if ch in "{(":
            depth += 1
        elif ch in "})":
            depth -= 1
        if ch == "," and depth == 0 and not in_quote:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    parts.append("".join(current))
    return parts


def _clean(value: str) -> str:
    value = value.strip()
    if value and value[0] in '{"' and value[-1] in '}"':
        value = value[1:-1]
    return value.strip()


def parse_bibtex(text: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for etype, body in _entry_bodies(text):
        parts = _split_top(body)
        if not parts:
            continue
        key = parts[0].strip()
        fields: dict[str, str] = {}
        for part in parts[1:]:
            if "=" not in part:
                continue
            name, _, raw = part.partition("=")
            name = name.strip().lower()
            if name in _WANT:
                fields[name] = _clean(raw)
        records.append(
            {
                "bib_key": key,
                "type": etype.lower(),
                "doi": fields.get("doi"),
                "title": fields.get("title"),
                "author": fields.get("author"),
                "year": fields.get("year"),
                "url": fields.get("url"),
            }
        )
    return records
