"""Drafting flow: diff preview and requested write (02 §5.6).

Agent text enters a unit only through ``rh unit write`` after a diff preview, on
the author's request. If a target paragraph changed since the agent read it, the
write is refused with a three-way diff (T07). On success paragraph origins are
set and the request is stored; the unit's claims rebind to the new text.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from research_harness.core.clock import default_clock
from research_harness.core.errors import BlockedError
from research_harness.structure import ops
from research_harness.units import anchors, diff
from research_harness.units.anchors import paragraph_sha

_FRONT = re.compile(r"^(---\n.*?\n---\n)(.*)$", re.DOTALL)


def _folder(root: Path, unit_id: str) -> Path:
    return ops.current_folders(root)[unit_id]


def _split(text: str) -> tuple[str, str]:
    m = _FRONT.match(text)
    return (m.group(1), m.group(2)) if m else ("", text)


def read_body(root: Path, unit_id: str) -> str:
    return _split((_folder(root, unit_id) / "text.md").read_text(encoding="utf-8"))[1]


def diff_preview(root: Path, unit_id: str, new_body: str) -> str:
    return diff.unified_diff(read_body(root, unit_id), new_body, unit_id)


def write_body(root: Path, unit_id: str, new_body: str, *, by: str) -> list[dict[str, str]]:
    """Low-level write used by the author/dictation path (no conflict check)."""
    from research_harness.provenance.paragraphs import apply_write

    folder = _folder(root, unit_id)
    front, _ = _split((folder / "text.md").read_text(encoding="utf-8"))
    anchored, paras = anchors.ensure_anchors(new_body)
    (folder / "text.md").write_text(front + anchored, encoding="utf-8")
    apply_write(root, unit_id, paras, by=by)
    rebind_claims(root, unit_id)
    return paras


def write_unit(
    root: Path,
    unit_id: str,
    new_body: str,
    *,
    request: str,
    base: dict[str, str] | None = None,
) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    """Agent write. Refuses if a target paragraph changed since ``base`` (T07)."""
    if not request or not request.strip():
        raise ValueError("a write needs the author's request (--request)")

    current = anchors.paragraph_map(read_body(root, unit_id))
    anchored, paras = anchors.ensure_anchors(new_body)
    ours = {p["id"]: p["text"] for p in paras if p["id"]}

    if base:
        conflicts = diff.three_way(base, ours, current)
        if conflicts:
            raise BlockedError(
                "error.author_edit_conflict",
                params={"paragraphs": ", ".join(c["paragraph_id"] for c in conflicts)},
            )

    folder = _folder(root, unit_id)
    front, _ = _split((folder / "text.md").read_text(encoding="utf-8"))
    (folder / "text.md").write_text(front + anchored, encoding="utf-8")

    from research_harness.provenance.paragraphs import apply_write

    apply_write(root, unit_id, paras, by="agent")
    rebind_claims(root, unit_id)
    _log_request(root, unit_id, request, paras)
    return paras, []


def _log_request(root: Path, unit_id: str, request: str, paras: list[dict[str, str]]) -> None:
    path = _folder(root, unit_id) / "write-log.jsonl"
    entry = {
        "at": default_clock().now_rfc3339(),
        "request": request,
        "paragraphs": [p["id"] for p in paras],
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def rebind_claims(root: Path, unit_id: str) -> int:
    """Rebind this unit's claims to the current paragraph text hashes (02 §6)."""
    folder = _folder(root, unit_id)
    cf = folder / "claims.json"
    if not cf.is_file():
        return 0
    data = json.loads(cf.read_text(encoding="utf-8"))
    pmap = anchors.paragraph_map(read_body(root, unit_id))
    rebound = 0
    for c in data.get("claims", []):
        pid = c.get("location", {}).get("paragraph_id")
        if pid and pid in pmap:
            new_sha = paragraph_sha(pmap[pid])
            if c["location"].get("text_sha256") != new_sha:
                c["location"]["text_sha256"] = new_sha
                rebound += 1
    if rebound:
        cf.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return rebound
