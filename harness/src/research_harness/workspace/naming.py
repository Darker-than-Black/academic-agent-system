"""Object folder naming (01 §4, FR-42, ADR-014)."""

from __future__ import annotations

import re

from research_harness.core.paths import sanitize_title

_SUFFIX = re.compile(r"__(A|T)-\d{4}-\d+$")


def object_folder_name(title: str, object_id: str) -> str:
    """``<sanitized, trimmed title>__<ID>``; the ID suffix is never cut."""
    base = sanitize_title(title) or "untitled"
    return f"{base}__{object_id}"


def id_from_folder(folder_name: str) -> str | None:
    m = _SUFFIX.search(folder_name)
    return folder_name[m.start() + 2 :] if m else None
