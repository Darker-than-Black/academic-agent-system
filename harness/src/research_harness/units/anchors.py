"""Paragraph anchors: each paragraph starts with an invisible HTML-comment
anchor ``<!-- PG-XXXXXX -->`` on its own line (claims-text.md [P]). Anchors
survive edits; a paragraph without one gets an anchor on the next operation.

Decision (recorded for M2-10): HTML-comment anchors, not a sidecar hash map.
They are invisible in rendered Markdown and are stripped on docx export by a
pandoc filter (verified in the M2-12 round-trip); the sidecar alternative loses
the anchor when a paragraph is split or merged by hand.
"""

from __future__ import annotations

import re
from typing import Any

from research_harness.core.hashing import text_hash
from research_harness.core.ulid import new_ulid

ANCHOR_RE = re.compile(r"<!--\s*(PG-[0-9A-HJKMNP-TV-Z]{6})\s*-->")


def new_pg_id() -> str:
    # The last 6 chars are ULID randomness (the first 10 are a shared timestamp,
    # which would collide for paragraphs created in the same millisecond).
    return "PG-" + new_ulid()[-6:]


def paragraph_sha(text: str) -> str:
    return text_hash(text.encode("utf-8"))


def parse(body: str) -> list[dict[str, str | None]]:
    """Split a unit body into paragraphs: {id (or None), text}."""
    paras: list[dict[str, str | None]] = []
    current: dict[str, Any] = {"id": None, "lines": []}

    def flush() -> None:
        text = "\n".join(current["lines"]).strip()
        if text or current["id"]:
            paras.append({"id": current["id"], "text": text})

    for line in body.splitlines():
        m = ANCHOR_RE.match(line.strip())
        if m:
            flush()
            current = {"id": m.group(1), "lines": []}
        elif not line.strip() and current["lines"]:
            flush()
            current = {"id": None, "lines": []}
        elif line.strip():
            current["lines"].append(line)
    flush()
    return [p for p in paras if p["text"]]


def ensure_anchors(body: str) -> tuple[str, list[dict[str, str]]]:
    """Return (body with an anchor on every paragraph, list of {id, text})."""
    paras = parse(body)
    out_lines: list[str] = []
    result: list[dict[str, str]] = []
    for p in paras:
        pid = p["id"] or new_pg_id()
        out_lines.append(f"<!-- {pid} -->")
        out_lines.append(p["text"])
        out_lines.append("")
        result.append({"id": pid, "text": p["text"]})
    return "\n".join(out_lines).rstrip() + "\n", result


def paragraph_map(body: str) -> dict[str, str]:
    """{paragraph_id: text} for paragraphs that already carry an anchor."""
    return {p["id"]: p["text"] for p in parse(body) if p["id"]}
