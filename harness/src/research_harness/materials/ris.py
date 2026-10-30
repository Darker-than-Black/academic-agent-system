"""Minimal, dependency-free RIS parsing (02 §9.2)."""

from __future__ import annotations

from typing import Any

_TAGS = {
    "DO": "doi",
    "TI": "title",
    "T1": "title",
    "PY": "year",
    "Y1": "year",
    "UR": "url",
    "AU": "author",
}


def parse_ris(text: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    for line in text.splitlines():
        if len(line) < 6 or line[2:6] != "  - ":
            continue
        tag, value = line[:2], line[6:].strip()
        if tag == "TY":
            if current:
                records.append(current)
            current = {"bib_key": f"ris{len(records) + 1}", "type": value}
        elif tag == "ER":
            if current:
                records.append(current)
            current = {}
        elif tag in _TAGS:
            field = _TAGS[tag]
            if field == "author":
                current.setdefault("author", "")
                current["author"] = (current["author"] + "; " + value).strip("; ")
            else:
                current[field] = value
    if current:
        records.append(current)
    return records
