"""Enter ``revise`` mode (M3-08/M3-09, lifecycle-records.md, FR-41).

Core, LLM-free (H5). Sets the intake mode to ``revise``, records the agreed
scope, keeps the imported original read-only, and proposes that every unit
*outside* the scope be locked — the author confirms each lock (``rh lock``),
never the agent (locks outside scope protect text the revision must not touch).
"""

from __future__ import annotations

import json
from pathlib import Path

from research_harness.intake.answers import answers_path
from research_harness.intake.answers import load as load_answers
from research_harness.state.snapshot import atomic_write_bytes
from research_harness.structure import ops


def enter_revise(root: Path, scope: list[str], *, original_md: str | None = None) -> dict:
    """Switch to revise mode with ``scope`` (unit ids). Returns a plain report
    with the scope and the units proposed for locking (outside the scope)."""
    data = load_answers(root)
    data["mode"] = "revise"
    atomic_write_bytes(
        answers_path(root),
        (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    )

    revise_dir = root / "revise"
    revise_dir.mkdir(parents=True, exist_ok=True)
    (revise_dir / "scope.json").write_text(
        json.dumps({"scope": scope}, ensure_ascii=False), encoding="utf-8"
    )
    if original_md is not None:
        orig = root / "manuscript" / "original"
        orig.mkdir(parents=True, exist_ok=True)
        (orig / "manuscript.md").write_text(original_md, encoding="utf-8")

    in_scope = set(scope)
    propose_lock = [uid for uid in ops.current_folders(root) if uid not in in_scope]
    return {"scope": scope, "propose_lock": sorted(propose_lock)}
