"""Context-pack composition per role (summaries-context.md table). Over budget
is an error that lists the items and sizes; nothing is truncated. The
orchestrator is refused a pack with the full text of more than one unit.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_harness.context.budget import budget_for, estimate_tokens, method
from research_harness.core.clock import default_clock
from research_harness.schemas import validate
from research_harness.structure import model, ops
from research_harness.units.brief import load_brief


def packs_dir(root: Path) -> Path:
    return root / "context" / "packs"


def _read(path: Path) -> str | None:
    return path.read_text(encoding="utf-8") if path.is_file() else None


def _item(ref: str, kind: str, text: str, *, full_text: bool = False) -> dict[str, Any]:
    return {
        "ref": ref,
        "kind": kind,
        "chars": len(text),
        "tokens": estimate_tokens(text),
        "full_text": full_text,
    }


def _find(units: list[model.Unit], target: str):
    """Return (node, parent, siblings) for target in the tree."""

    def walk(nodes, parent):
        for n in nodes:
            if n.id == target:
                return n, parent, nodes
            hit = walk(n.children, n)
            if hit:
                return hit
        return None

    return walk(units, None) or (None, None, [])


def _leaves(node: model.Unit) -> list[str]:
    if not node.children:
        return [node.id]
    out: list[str] = []
    for c in node.children:
        out.extend(_leaves(c))
    return out


def _assemble(root: Path, target_id: str, role: str) -> list[dict[str, Any]]:
    folders = ops.current_folders(root)
    units = model.parse_units(model.load(root))
    node, parent, siblings = _find(units, target_id)
    man = root / "manuscript"
    items: list[dict[str, Any]] = []

    def add(ref, kind, path: Path, full_text=False):
        text = _read(path)
        if text is not None:
            items.append(_item(ref, kind, text, full_text=full_text))

    def unit_folder(uid: str) -> Path | None:
        return folders.get(uid)

    if role in ("writer", "unit_critic", "summarizer"):
        uf = unit_folder(target_id)
        if role in ("unit_critic", "summarizer") and uf:
            add(f"text:{target_id}", "unit_text", uf / "text.md", full_text=True)
        if role in ("writer", "unit_critic") and uf:
            add(f"brief:{target_id}", "brief", uf / "brief.md")
        if role == "writer":
            add("map:document", "map", man / "map.md")
            if parent is not None:
                p = root / "summaries" / f"{parent.id}.json"
                add(f"chapter_summary:{parent.id}", "chapter_summary", p)
            for sib in siblings:
                if sib.id != target_id and (sf := unit_folder(sib.id)):
                    add(f"summary:{sib.id}", "neighbour_summary", sf / "summary.md")
            _add_evidence(root, target_id, items)
            add("style:profile", "style_profile", root / "profiles" / "style.md")
        add("glossary:document", "glossary", man / "glossary.md")

    elif role == "analyst":
        add("map:document", "map", man / "map.md")
        add("glossary:document", "glossary", man / "glossary.md")
        add("findings:synthesis", "findings", root / "lab" / "findings.yaml")

    elif role == "orchestrator":
        add("map:document", "map", man / "map.md")
        leaves = _leaves(node) if node else list(folders)
        for uid in leaves:
            if sf := unit_folder(uid):
                add(f"summary:{uid}", "summary", sf / "summary.md")
        # A naive full-text request: one unit is fine, a whole chapter is refused.
        for uid in leaves:
            if uf := unit_folder(uid):
                add(f"text:{uid}", "unit_text", uf / "text.md", full_text=True)

    return items


def _add_evidence(root: Path, unit_id: str, items: list[dict[str, Any]]) -> None:
    from research_harness.evidence.excerpts import load_excerpts

    brief, _ = load_brief(root, unit_id)
    refs = {r for r in brief.get("evidence_refs", []) if r.startswith("excerpt:")}
    if not refs:
        return
    idx = {f"excerpt:{e['id']}": e for e in load_excerpts(root)}
    for ref in sorted(refs):
        exc = idx.get(ref)
        if exc:
            items.append(_item(ref, "evidence", exc["text"]))


def _next_id(root: Path) -> str:
    d = packs_dir(root)
    n = len(list(d.glob("CP-*.json"))) + 1 if d.is_dir() else 1
    return f"CP-{n}"


def build_pack(
    root: Path, target_id: str, role: str, *, budget: int | None = None
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    items = _assemble(root, target_id, role)
    total = sum(i["tokens"] for i in items)
    max_tokens = budget if budget is not None else budget_for(role)
    full_units = [i for i in items if i.get("full_text")]
    refused = role == "orchestrator" and len(full_units) > 1
    within = total <= max_tokens and not refused

    manifest: dict[str, Any] = {
        "schema_version": "0.2",
        "id": _next_id(root),
        "role": role,
        "target_id": target_id,
        "created_at": default_clock().now_rfc3339(),
        "budget": {"max_tokens": max_tokens, "method": method()},
        "items": items,
        "total_tokens": total,
        "within_budget": within,
        "refused": refused,
    }
    errors = validate("context-pack", manifest)
    if errors:
        raise ValueError(f"invalid context pack: {errors}")

    findings: list[dict[str, Any]] = []
    if refused:
        findings.append(
            {
                "check_id": "context.orchestrator_fulltext",
                "severity": "blocker",
                "reason": (
                    "orchestrator may not receive the full text of more than one unit (NFR-16)"
                ),
                "location": {},
                "proposed_action": "",
            }
        )
    elif not within:
        findings.append(
            {
                "check_id": "context.over_budget",
                "severity": "blocker",
                "reason": (
                    f"pack is {total} tokens over the {max_tokens}-token budget; no truncation"
                ),
                "location": {},
                "proposed_action": "",
            }
        )

    if within:
        packs_dir(root).mkdir(parents=True, exist_ok=True)
        (packs_dir(root) / f"{manifest['id']}.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return manifest, findings
