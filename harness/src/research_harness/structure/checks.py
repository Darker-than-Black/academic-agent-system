"""Structure-scope checks: invariants of 02 §7.2."""

from __future__ import annotations

import json
from pathlib import Path

from research_harness.structure import model
from research_harness.structure.naming import compute_paths
from research_harness.structure.ops import _flatten, _front_matter, current_folders
from research_harness.validate.framework import Finding, ValidationContext, finding, registry

CHECK_ID = "structure.invariant"
UNIT_FILES = ("text.md", "brief.md", "summary.md", "claims.json")


def check_structure(root: Path, main_language: str = "uk") -> list[Finding]:
    findings: list[Finding] = []
    data = model.load(root)
    units = model.parse_units(data)
    flat = _flatten(units)

    ids = [u.id for u in flat]
    for uid in {i for i in ids if ids.count(i) > 1}:
        findings.append(
            finding(
                check_id=CHECK_ID,
                severity="blocker",
                reason=f"duplicate unit id {uid}",
                ref=f"unit:{uid}",
            )
        )

    labels = model.resolve_labels(data, main_language)
    desired = compute_paths(units, labels)
    folders = current_folders(root)
    by_id = {u.id: u for u in flat}

    for uid, rel in desired.items():
        folder = root / rel
        if not folder.is_dir():
            findings.append(
                finding(
                    check_id=CHECK_ID,
                    severity="major",
                    reason=f"unit {uid}: expected folder {rel} is missing",
                    ref=f"unit:{uid}",
                    proposed_action="rh structure sync",
                )
            )
            continue
        for fn in UNIT_FILES:
            if not (folder / fn).is_file():
                findings.append(
                    finding(
                        check_id=CHECK_ID,
                        severity="major",
                        reason=f"unit {uid}: missing {fn}",
                        ref=f"unit:{uid}",
                        proposed_action="rh structure sync",
                    )
                )
        fm = _front_matter((folder / "text.md").read_text(encoding="utf-8"))
        if fm.get("id") != uid:
            findings.append(
                finding(
                    check_id=CHECK_ID,
                    severity="major",
                    reason=f"front-matter id {fm.get('id')!r} != structure id {uid!r}",
                    ref=f"unit:{uid}",
                )
            )
        if (by_id[uid].title or "") != (fm.get("title") or ""):
            findings.append(
                finding(
                    check_id=CHECK_ID,
                    severity="minor",
                    reason=f"unit {uid}: title differs from structure.yaml",
                    ref=f"unit:{uid}",
                    proposed_action="rh structure sync",
                )
            )

    # Every unit folder on disk must be declared in structure.yaml.
    declared = set(desired)
    for uid in folders:
        if uid not in declared:
            findings.append(
                finding(
                    check_id=CHECK_ID,
                    severity="major",
                    reason=f"folder for unit {uid} is not in structure.yaml",
                    ref=f"unit:{uid}",
                )
            )
    return findings


@registry.register(id=CHECK_ID, version="1", scope="structure")
def _structure_check(ctx: ValidationContext) -> list[Finding]:
    root = ctx.extra.get("object_root")
    if root is None:
        return []
    root = Path(root)
    if not (root / "structure.yaml").is_file():
        return []
    main_language = "uk"
    obj = root / "object.json"
    if obj.is_file():
        try:
            main_language = (
                json.loads(obj.read_text(encoding="utf-8")).get("languages", {}).get("main", "uk")
            )
        except json.JSONDecodeError:
            pass
    return check_structure(root, main_language)
