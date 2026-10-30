"""Assemble the manuscript in structure order and drive a draft export:
``.docx`` (pandoc) or ``.md``, plus references.bib, gaps.md and a manifest whose
hashes match the written files (T46, T11, T43)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_harness.claims import ledger as ledger_mod
from research_harness.core.clock import default_clock
from research_harness.core.hashing import file_hash
from research_harness.export_docx import pandoc, references
from research_harness.export_docx.bookmarks import bookmark_map
from research_harness.structure import model, ops
from research_harness.units import anchors
from research_harness.units.write import read_body

_PLACEHOLDER = "[[AUTHOR:"
_WEAK = ("unreviewed", "insufficient", "not_found", "contradicted", "unverifiable")
_MATERIAL = ("critical", "material")
# format pack lives in harness/rulepacks/<pack>/ (format part, M2-12)
_PACK_DIR = Path(__file__).resolve().parents[3] / "rulepacks"


def _ordered_ids(root: Path) -> list[str]:
    order: list[str] = []

    def walk(nodes):
        for n in nodes:
            order.append(n.id)
            walk(n.children)

    walk(model.parse_units(model.load(root)))
    return order


def assemble_markdown(root: Path) -> str:
    folders = ops.current_folders(root)
    units = model.parse_units(model.load(root))
    title = {u.id: u.title for u in _flatten(units)}
    out: list[str] = []
    for uid in _ordered_ids(root):
        folder = folders.get(uid)
        if folder is None or not (folder / "text.md").is_file():
            continue
        body = anchors.ANCHOR_RE.sub("", read_body(root, uid)).strip()
        out.append(f"# {title.get(uid, uid)}\n\n{body}")
    return "\n\n".join(out) + "\n"


def _flatten(units):
    for u in units:
        yield u
        yield from _flatten(u.children)


def _gaps(root: Path) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    folders = ops.current_folders(root)
    for uid in folders:
        body = read_body(root, uid)
        if _PLACEHOLDER in body:
            gaps.append(_g("export.placeholder", f"{uid} has unresolved author placeholders"))
        for claim in ledger_mod.load_unit_claims(root, uid):
            if (
                claim.get("materiality") in _MATERIAL
                and claim.get("support", "unreviewed") in _WEAK
            ):
                gaps.append(
                    _g(
                        "export.claim_unsupported",
                        f"{uid} {claim['id']}: support {claim.get('support')!r}",
                    )
                )
    try:
        from research_harness.summaries import map as map_mod

        for uid, stale in map_mod.stale_report(root).items():
            if stale:
                gaps.append(_g("export.summary_stale", f"{uid}: summary is stale"))
    except Exception:  # noqa: BLE001 — summaries are optional for a draft
        pass
    return gaps


def export_draft(root: Path, *, fmt: str = "md", pack: str = "ua-fahove-b") -> dict[str, Any]:
    clock = default_clock()
    stamp = clock.now_rfc3339().replace(":", "").replace("-", "")
    outdir = root / "export" / stamp
    outdir.mkdir(parents=True, exist_ok=True)

    md_path = outdir / "manuscript.md"
    md_path.write_text(assemble_markdown(root), encoding="utf-8")

    bib, ref_gaps = references.build(root)
    (outdir / "references.bib").write_text(bib, encoding="utf-8")

    gaps = ref_gaps + _gaps(root)
    (outdir / "gaps.md").write_text(_render_gaps(gaps), encoding="utf-8")

    produced = md_path
    fmt_used = "md"
    if fmt == "docx" and pandoc.have_pandoc():
        ref_docx = _PACK_DIR / pack / "reference.docx"
        csl = _PACK_DIR / pack / "csl" / "dstu-8302-2015.csl"
        produced = pandoc.to_docx(
            md_path,
            outdir / "manuscript.docx",
            reference_docx=ref_docx if ref_docx.is_file() else None,
            csl=csl if csl.is_file() else None,
            bib=outdir / "references.bib",
        )
        fmt_used = "docx"

    files = [p for p in (produced, outdir / "references.bib", outdir / "gaps.md") if p.is_file()]
    manifest = {
        "schema_version": "0.2",
        "created_at": clock.now_rfc3339(),
        "mode": "draft",
        "format": fmt_used,
        "pack": pack,
        "files": [{"path": p.name, "sha256": file_hash(p)} for p in files],
        "bookmarks": bookmark_map(root),
        "gaps": len(gaps),
    }
    (outdir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {"dir": str(outdir), "format": fmt_used, "gaps": gaps, "manifest": manifest}


def _render_gaps(gaps: list[dict[str, Any]]) -> str:
    if not gaps:
        return "# Gaps\n\nNone found.\n"
    lines = ["# Gaps\n"]
    for g in gaps:
        lines.append(f"- **{g['check_id']}** — {g['reason']}")
    return "\n".join(lines) + "\n"


def _g(check_id: str, reason: str) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "severity": "major",
        "reason": reason,
        "location": {},
        "proposed_action": "",
    }
