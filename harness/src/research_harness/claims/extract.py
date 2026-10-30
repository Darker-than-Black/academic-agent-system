"""Claim extraction (baseline, M2): split a unit's text into paragraph-level
candidate claim stubs for the author/critic to confirm. Advisory only — it
never stores a claim or a verdict on its own (recall measured as MX, T06).
"""

from __future__ import annotations

import re

_ANCHOR = re.compile(r"<!--\s*PG-[0-9A-Za-z]+\s*-->")
_SENTENCE = re.compile(r"(?<=[.!?])\s+")


def candidate_claims(text: str) -> list[dict[str, str]]:
    """Return candidate claim stubs (one per non-trivial sentence)."""
    stubs: list[dict[str, str]] = []
    paragraph_id = ""
    for line in text.splitlines():
        anchor = _ANCHOR.search(line)
        if anchor:
            paragraph_id = anchor.group(0).strip("<!->").strip()
            continue
        line = line.strip()
        if not line:
            continue
        for sentence in _SENTENCE.split(line):
            s = sentence.strip()
            if len(s) >= 20:  # skip trivial fragments
                stubs.append({"text": s, "paragraph_id": paragraph_id})
    return stubs
