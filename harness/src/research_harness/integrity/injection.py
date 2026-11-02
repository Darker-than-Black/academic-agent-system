"""Prompt-injection scan for imported text (integrity.md; M3-14, FR-16, T14).

Text from sources, PDFs, web pages, .docx or tool output is data, never
instructions (H10). This deterministic scan flags imperative patterns addressed
to an assistant and URLs carrying tokens, so the author sees them as findings;
the content is never executed and secrets never enter a context pack.
"""

from __future__ import annotations

import re
from typing import Any

_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("ignore_previous", re.compile(r"ignore\s+(all\s+)?(the\s+)?previous\s+instructions", re.I)),
    ("disregard_above", re.compile(r"disregard\s+(the\s+)?(above|previous)", re.I)),
    ("as_an_ai", re.compile(r"as\s+an?\s+ai\s+(language\s+)?model", re.I)),
    ("you_are_now", re.compile(r"you\s+are\s+now\b", re.I)),
    ("system_prompt", re.compile(r"system\s*prompt", re.I)),
    ("new_instructions", re.compile(r"\bnew\s+instructions\s*:", re.I)),
    (
        "reveal_or_send",
        re.compile(
            r"\b(reveal|exfiltrate|send|email|upload)\b.{0,40}\b(key|secret|token|password|prompt)\b",
            re.I,
        ),
    ),
    (
        "url_with_token",
        re.compile(r"https?://[^\s'\"]*[?&](?:api_?key|token|access_token)=[^\s'\"&]+", re.I),
    ),
    ("ua_ignore", re.compile(r"\bігноруй\s+(усі\s+|всі\s+)?попередн", re.I)),
    ("ua_disregard", re.compile(r"\bнехтуй\s+попередн", re.I)),
)


def scan(text: str, location: Any = None) -> list[dict[str, Any]]:
    """Return ``integrity.prompt_injection`` findings for ``text`` (empty = clean).

    ``location`` is attached verbatim (e.g. a unit id, page, paragraph) so the
    author can find the fragment. At most one finding per pattern."""
    findings: list[dict[str, Any]] = []
    for name, pattern in _PATTERNS:
        m = pattern.search(text)
        if not m:
            continue
        findings.append(
            {
                "check_id": "integrity.prompt_injection",
                "severity": "major",
                "reason": f"instruction-like text ({name}): {m.group(0)!r} (data, not executed)",
                "location": location if location is not None else {},
                "observed": m.group(0),
                "proposed_action": "Treat as data; keep it out of any instruction or context pack.",
            }
        )
    return findings
