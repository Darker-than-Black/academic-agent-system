"""Unit and paragraph diffs shown before an agent edit is applied (02 §5.6).

Adapted from AutoResearchClaw researchclaw/hitl/diff_view.py (MIT,
commit be4ba4755bf1b52220f25e13b2293b5956590070): kept unified_diff,
side_by_side_diff, diff_summary and format_diff_stats; dropped the
pipeline-snapshot helper; added paragraph-level three-way conflict detection.
difflib works on Unicode, so diffs are Cyrillic-safe.
"""

from __future__ import annotations

import difflib
from typing import Any


def unified_diff(original: str, modified: str, filename: str = "unit") -> str:
    if original == modified:
        return "No changes"
    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        modified.splitlines(keepends=True),
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm="",
    )
    return "".join(diff) or "No changes"


def diff_summary(original: str, modified: str) -> dict[str, int]:
    orig_lines = original.splitlines()
    mod_lines = modified.splitlines()
    sm = difflib.SequenceMatcher(None, orig_lines, mod_lines)
    stats = {"added": 0, "deleted": 0, "changed": 0, "unchanged": 0}
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            stats["unchanged"] += i2 - i1
        elif tag == "replace":
            stats["changed"] += max(i2 - i1, j2 - j1)
        elif tag == "delete":
            stats["deleted"] += i2 - i1
        elif tag == "insert":
            stats["added"] += j2 - j1
    return stats


def format_diff_stats(stats: dict[str, int]) -> str:
    parts = []
    if stats["added"]:
        parts.append(f"+{stats['added']} added")
    if stats["deleted"]:
        parts.append(f"-{stats['deleted']} deleted")
    if stats["changed"]:
        parts.append(f"~{stats['changed']} changed")
    parts.append(f"{stats['unchanged']} unchanged")
    return ", ".join(parts)


def three_way(
    base: dict[str, str], ours: dict[str, str], theirs: dict[str, str]
) -> list[dict[str, Any]]:
    """Per-paragraph three-way conflict detection by paragraph id.

    ``base`` is what the agent read; ``ours`` is the agent's proposed text;
    ``theirs`` is the current on-disk text. A paragraph the agent changed that
    the author also changed since base is a conflict (T07).
    """
    conflicts: list[dict[str, Any]] = []
    for pid, base_text in base.items():
        agent_changed = ours.get(pid, base_text) != base_text
        author_changed = theirs.get(pid, base_text) != base_text
        if agent_changed and author_changed and ours.get(pid) != theirs.get(pid):
            conflicts.append(
                {
                    "paragraph_id": pid,
                    "base": base_text,
                    "ours": ours.get(pid, ""),
                    "theirs": theirs.get(pid, ""),
                    "diff": unified_diff(theirs.get(pid, ""), ours.get(pid, ""), pid),
                }
            )
    return conflicts
