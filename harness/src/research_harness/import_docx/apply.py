"""Import a reviewed ``.docx``: parse, map, record, and enter the revise flow.

The command never writes manuscript text (H13). It records the original and the
parsed changes under ``history/imports/<ts>/``, builds a per-unit diff for the
author to review, raises a blocker for anything unmapped (T46), and enters
``revise`` mode scoped to the touched units. The author then accepts changes
through the write path, which sets each paragraph's origin per change author
(FR-53); ``proposed_origin`` in the plan previews that without applying it.
"""

from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path
from typing import Any

from research_harness.core.clock import default_clock
from research_harness.core.errors import BlockedError
from research_harness.import_docx import map_units
from research_harness.import_docx.parse import Change, parse_docx
from research_harness.lifecycle.revise import enter_revise
from research_harness.provenance import paragraphs as prov
from research_harness.schemas import validate
from research_harness.structure import ops
from research_harness.units import anchors
from research_harness.units.write import read_body


def _change_dict(c: Change) -> dict[str, Any]:
    return {
        "type": c.type,
        "author": c.author,
        "date": c.date,
        "text": c.text,
        "unit_id": c.unit_id,
        "paragraph_id": c.paragraph_id,
        "change_id": c.change_id,
    }


def _finding(check_id: str, reason: str, *, observed: Any = None) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "severity": "blocker",
        "reason": reason,
        "location": {},
        "observed": observed,
        "proposed_action": "Resolve before accepting the import (rh revise / rh lock).",
    }


def _proposed_origin(root: Path, unit_id: str, paragraph_id: str | None) -> str:
    """Origin a human edit would set when accepted (FR-53): a human edit to an
    agent paragraph becomes ``agent_edited_by_author``; otherwise ``author``."""
    if paragraph_id:
        current = prov.load_map(root, unit_id).get(paragraph_id)
        if current and current.get("origin") == "agent":
            return "agent_edited_by_author"
    return "author"


def _unit_diffs(root: Path, unit_id: str, changes: list[Change], accepted: dict[str, str]) -> dict:
    from research_harness.units import diff as diff_mod

    current = anchors.paragraph_map(read_body(root, unit_id))
    diffs: list[dict[str, Any]] = []
    for pid in sorted({c.paragraph_id for c in changes if c.paragraph_id}):
        if pid not in accepted:
            continue
        old = current.get(pid, "")
        new = accepted[pid]
        if old == new:
            continue
        diffs.append(
            {
                "paragraph_id": pid,
                "proposed_origin": _proposed_origin(root, unit_id, pid),
                "accepted_text": new,
                "diff": diff_mod.unified_diff(old, new, f"{unit_id}/{pid}"),
            }
        )
    return {
        "unit_id": unit_id,
        "changes": [_change_dict(c) for c in changes],
        "diffs": diffs,
    }


def import_docx(
    root: Path,
    docx_path: Path,
    *,
    source: str = "editor",
    actor_label: str | None = None,
) -> dict[str, Any]:
    path = Path(docx_path)
    if not path.is_file():
        raise BlockedError("error.import_file_missing", params={"path": str(path)})
    if path.suffix.lower() != ".docx" or not zipfile.is_zipfile(path):
        raise BlockedError("error.import_not_docx", params={"path": str(path)})

    parsed = parse_docx(path)
    mapped, unmapped = map_units.map_changes(root, parsed.changes)

    clock = default_clock()
    stamp = clock.now_rfc3339().replace(":", "").replace("-", "")
    imp = root / "history" / "imports" / stamp
    imp.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, imp / "original.docx")

    record = {
        "schema_version": "0.2",
        "created_at": clock.now_rfc3339(),
        "source": source,
        "actor_label": actor_label,
        "count": parsed.count,
        "mapped": len(mapped),
        "unmapped": len(unmapped),
        "changes": [_change_dict(c) for c in parsed.changes],
    }
    errors = validate("import-record", record)
    if errors:
        raise ValueError(f"invalid import record: {errors}")
    (imp / "changes.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if unmapped:
        (imp / "unmapped.json").write_text(
            json.dumps([_change_dict(c) for c in unmapped], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    findings: list[dict[str, Any]] = []
    total = len(mapped) + len(unmapped)
    if parsed.count != total:
        findings.append(
            _finding(
                "import.count_mismatch",
                f"parsed {parsed.count} changes but accounted for {total} (mapped+unmapped)",
                observed={"count": parsed.count, "mapped": len(mapped), "unmapped": len(unmapped)},
            )
        )
    if unmapped:
        findings.append(
            _finding(
                "import.unmapped_changes",
                f"{len(unmapped)} change(s) could not be mapped to a unit (bookmark deleted?)",
                observed=len(unmapped),
            )
        )

    folders = ops.current_folders(root)
    by_unit: dict[str, list[Change]] = {}
    for c in mapped:
        by_unit.setdefault(c.unit_id, []).append(c)  # type: ignore[arg-type]
    units = [
        _unit_diffs(root, uid, by_unit[uid], parsed.accepted)
        for uid in sorted(by_unit)
        if uid in folders
    ]
    plan = {"schema_version": "0.2", "units": units}
    (imp / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    (imp / "diff.md").write_text(_render_diff(units), encoding="utf-8")

    touched = sorted(by_unit)
    original_md = _assemble_accepted(by_unit, parsed.accepted, root)
    revise = enter_revise(root, touched, original_md=original_md)

    return {
        "dir": str(imp),
        "count": parsed.count,
        "mapped": len(mapped),
        "unmapped": len(unmapped),
        "units": touched,
        "findings": findings,
        "blocked": bool(findings),
        "revise": revise,
    }


def _assemble_accepted(
    by_unit: dict[str, list[Change]], accepted: dict[str, str], root: Path
) -> str:
    """A Markdown snapshot of the imported manuscript with changes applied, in
    unit order, kept read-only under ``manuscript/original/`` for the revision."""
    from research_harness.structure import model

    title = {u.id: u.title for u in _flatten(model.parse_units(model.load(root)))}
    out: list[str] = []
    for uid in by_unit:
        paras = [accepted[c.paragraph_id] for c in by_unit[uid] if c.paragraph_id in accepted]
        seen: list[str] = []
        for p in paras:
            if p not in seen:
                seen.append(p)
        out.append(f"# {title.get(uid, uid)}\n\n" + "\n\n".join(seen))
    return "\n\n".join(out) + "\n"


def _flatten(units):
    for u in units:
        yield u
        yield from _flatten(u.children)


def _render_diff(units: list[dict[str, Any]]) -> str:
    if not units:
        return "# Import — no mapped changes\n"
    lines = ["# Import — proposed changes per unit\n"]
    for u in units:
        lines.append(f"## {u['unit_id']}\n")
        if not u["diffs"]:
            lines.append("_No textual diff (comments only)._\n")
        for d in u["diffs"]:
            lines.append(f"### {d['paragraph_id']} → origin `{d['proposed_origin']}`\n")
            lines.append("```diff")
            lines.append(d["diff"].rstrip())
            lines.append("```\n")
    return "\n".join(lines) + "\n"
