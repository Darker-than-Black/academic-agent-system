"""Resolve the rule stack for an object and write profiles/resolved-stack.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_harness.rules.loader import Pack, load_pack
from research_harness.rules.resolver import ResolvedStack, build_resolved_stack, resolve
from research_harness.rules.selector import select_packs
from research_harness.state.snapshot import atomic_write_bytes

RULEPACKS = Path(__file__).resolve().parents[3] / "rulepacks"

# Intake answers that map onto object.json's own fields. `venue`/`regulator`
# live in the resolved rule stack, not on the object, so they are not here.
# Allowed values mirror object.schema.json / common.schema.json ($defs); keep
# in sync with the schema.
_OBJECT_FIELD_FOR = {"Q2": "document_kind", "Q5": "study_kind"}
_ALLOWED_VALUES = {
    "document_kind": {"article", "thesis", "conference_abstract", "report", "unknown"},
    "study_kind": {
        "literature",
        "conceptual",
        "empirical_quantitative",
        "empirical_qualitative",
        "computational_ml",
        "mixed",
        "unknown",
    },
}


def persist_intake_object_fields(root: Path) -> bool:
    """Write known intake answers (Q2→document_kind, Q5→study_kind) onto
    object.json so readers like ``protocol.study_kind`` see them. An ``unknown``
    answer or a value outside the schema enum is never written (H7). Returns
    True when object.json changed. Call before the intake checkpoint so the
    change lands in the same snapshot.
    """
    intake = root / "intake" / "answers.json"
    if not intake.is_file():
        return False
    stored = json.loads(intake.read_text(encoding="utf-8")).get("answers", {})
    obj_path = root / "object.json"
    obj = json.loads(obj_path.read_text(encoding="utf-8"))
    changed = False
    for qid, field in _OBJECT_FIELD_FOR.items():
        ans = stored.get(qid)
        if not ans:
            continue
        value = ans.get("value")
        if value in (None, "unknown") or value not in _ALLOWED_VALUES[field]:
            continue
        if obj.get(field) != value:
            obj[field] = value
            changed = True
    if changed:
        atomic_write_bytes(
            obj_path, (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        )
    return changed


def all_packs(packs_dir: Path | None = None) -> list[Pack]:
    base = packs_dir or RULEPACKS
    return [load_pack(d) for d in sorted(base.iterdir()) if (d / "pack.yaml").is_file()]


def object_answers(root: Path) -> dict[str, Any]:
    obj = json.loads((root / "object.json").read_text(encoding="utf-8"))
    ans: dict[str, Any] = {
        "document_kind": obj.get("document_kind"),
        "study_kind": obj.get("study_kind"),
    }
    intake = root / "intake" / "answers.json"
    if intake.is_file():
        stored = json.loads(intake.read_text(encoding="utf-8")).get("answers", {})
        mapping = {"Q2": "document_kind", "Q4": "venue", "Q5": "study_kind", "Q6": "regulator"}
        for qid, field in mapping.items():
            if qid in stored and stored[qid]["value"] != "unknown":
                ans[field] = stored[qid]["value"]
    return ans


def resolve_object(
    root: Path, *, packs_dir: Path | None = None, write: bool = True
) -> tuple[ResolvedStack, list[Pack]]:
    packs = select_packs(all_packs(packs_dir), object_answers(root))
    stack = resolve(packs)
    if write:
        inputs = [{"ref": f"rulepack:{p.id}@{p.version}", "sha256": p.sha256} for p in packs]
        doc = build_resolved_stack(stack, inputs)
        (root / "profiles").mkdir(parents=True, exist_ok=True)
        atomic_write_bytes(
            root / "profiles" / "resolved-stack.json",
            (json.dumps(doc, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
        )
    return stack, packs
