"""Host-run alignment (M2-19): map a blind raw run to gold claim_ids.

A semantic host run is produced in two steps so the baseline stays honest (H6):

1. **Blind run** — orchestrator + subagents see only ``manuscript.md`` +
   ``sources.yaml`` + local full texts, never ``annotation.yaml``. They emit a
   *raw* run (``eval_run.raw`` schema): each claim carries a ``local_id`` and a
   verbatim ``anchor.quote`` from the manuscript, plus the model's own verdict
   and flagged defects.
2. **Alignment** (this module) — resolve each anchor quote to its manuscript
   span and assign the gold ``claim_id`` by **span overlap only**. Verdicts and
   defects are carried over **unchanged from the raw run**; nothing from the
   annotation except the ``claim_id`` string ever enters the output. The raw run
   is sha256-sealed into ``producer.note`` so a later edit is detectable.

Core and LLM-free (H5): nothing here calls a model. Only ``extracted`` and
``reviewed`` need alignment — ``integration_findings`` score by ``defect_id`` and
``contribution_points`` (MA) are self-labelled, so both pass through untouched.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml

from research_harness.core.errors import InvalidInputError

# Minimum char overlap (fraction of the shorter span) for a raw anchor to be
# accepted as the same claim as a gold span (author decision, M2-19 Q2).
OVERLAP_MIN = 0.5


# --- manuscript geometry (must match research_harness_dev.fixtures.f4w_annotation) ---
def paragraphs(text: str) -> list[str]:
    """Body paragraphs, globally indexed, matching the annotation generator."""
    body = re.sub(r"(?s)^---.*?---\n", "", text, count=1)
    body = re.sub(r"(?m)^#.*$", "", body)
    return [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]


def _variants(s: str) -> list[str]:
    out = {s}
    for a in ("'", "’", "ʼ"):
        for b in ("'", "’", "ʼ"):
            out.add(s.replace(a, b))
    return list(out)


def resolve(paras: list[str], quote: str) -> tuple[int, int, int] | None:
    """Locate ``quote`` as a unique substring of exactly one paragraph.

    Returns ``(paragraph_index, start, end)`` or ``None`` when the quote is
    missing or ambiguous — never a guessed position (H7).
    """
    hits: list[tuple[int, int, int]] = []
    for i, p in enumerate(paras):
        for v in _variants(quote):
            idx = p.find(v)
            if idx != -1 and p.find(v, idx + 1) == -1:
                hits.append((i, idx, idx + len(v)))
                break
    return hits[0] if len(hits) == 1 else None


def _overlap(a: tuple[int, int, int], b: tuple[int, int, int]) -> int:
    """Character overlap of two spans; 0 unless they share a paragraph."""
    if a[0] != b[0]:
        return 0
    return max(0, min(a[2], b[2]) - max(a[1], b[1]))


def _match(
    gold: dict[str, tuple[int, int, int]], raw: dict[str, tuple[int, int, int]]
) -> dict[str, str]:
    """Greedy 1:1 span-overlap match → ``{local_id: gold_claim_id}`` (M2-19 Q4)."""
    pairs: list[tuple[int, float, str, str]] = []
    for cid, gs in gold.items():
        for lid, rs in raw.items():
            ov = _overlap(gs, rs)
            if ov <= 0:
                continue
            shorter = min(gs[2] - gs[1], rs[2] - rs[1]) or 1
            ratio = ov / shorter
            if ratio >= OVERLAP_MIN:
                pairs.append((ov, ratio, cid, lid))
    # Deterministic: largest overlap first, then ratio, then ids.
    pairs.sort(key=lambda t: (-t[0], -t[1], t[2], t[3]))
    taken_gold: set[str] = set()
    taken_raw: set[str] = set()
    out: dict[str, str] = {}
    for _ov, _r, cid, lid in pairs:
        if cid in taken_gold or lid in taken_raw:
            continue
        taken_gold.add(cid)
        taken_raw.add(lid)
        out[lid] = cid
    return out


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# --- alignment ----------------------------------------------------------------
def align(raw: dict[str, Any], annotation: dict[str, Any], manuscript: str) -> dict[str, Any]:
    """Build an ``eval_run`` dict from a raw run + the gold annotation.

    Pure: carries over the raw verdicts/defects; assigns gold ``claim_id`` by
    span overlap; marks unmatched extracted claims spurious (``claim_id: null``).
    Returns ``{"run": <eval_run>, "report": {...}}``.
    """
    paras = paragraphs(manuscript)
    gold_spans: dict[str, tuple[int, int, int]] = {}
    for c in annotation.get("claims", []):
        s = c.get("span") or {}
        if all(k in s for k in ("paragraph", "start", "end")):
            gold_spans[c["claim_id"]] = (s["paragraph"], s["start"], s["end"])

    raw_spans: dict[str, tuple[int, int, int]] = {}
    unresolved: list[str] = []
    for e in raw.get("extracted", []):
        lid = e.get("local_id")
        quote = (e.get("anchor") or {}).get("quote", "")
        span = resolve(paras, quote) if quote else None
        if span is None:
            unresolved.append(lid)
        else:
            raw_spans[lid] = span

    local_to_gold = _match(gold_spans, raw_spans)

    extracted = [
        {
            "claim_id": local_to_gold.get(e.get("local_id")),
            "material": bool(e.get("material", True)),
        }
        for e in raw.get("extracted", [])
    ]
    reviewed = []
    for r in raw.get("reviewed", []):
        cid = local_to_gold.get(r.get("local_id"))
        if cid is None:
            continue  # unmatched verdict has no gold claim to score against
        item = {"claim_id": cid, "verdict": r.get("verdict")}
        if r.get("flagged_defects"):
            item["flagged_defects"] = list(r["flagged_defects"])
        reviewed.append(item)

    producer = dict(raw.get("producer") or {})
    run = {
        "schema_version": raw.get("schema_version", "0.2"),
        "fixture": raw.get("fixture", annotation.get("fixture", "")),
        "run_kind": raw.get("run_kind", "host"),
        "producer": producer,
        "extracted": extracted,
        "reviewed": reviewed,
        "integration_findings": list(raw.get("integration_findings", [])),
        "contribution_points": list(raw.get("contribution_points", [])),
    }
    report = {
        "gold_total": len(gold_spans),
        "raw_total": len(raw.get("extracted", [])),
        "matched": len(local_to_gold),
        "spurious": sum(1 for e in extracted if e["claim_id"] is None),
        "unresolved": unresolved,
    }
    return {"run": run, "report": report}


def align_files(
    raw_path: Path, annotation_path: Path, manuscript_path: Path, out_path: Path
) -> dict:
    """Read the raw run + annotation, align, seal the raw sha256, write ``out_path``."""
    if not raw_path.is_file():
        raise InvalidInputError("error.align_no_raw")
    if not annotation_path.is_file():
        raise InvalidInputError("error.align_no_annotation")
    if not manuscript_path.is_file():
        raise InvalidInputError("error.align_no_manuscript")
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    annotation = yaml.safe_load(annotation_path.read_text(encoding="utf-8"))
    manuscript = manuscript_path.read_text(encoding="utf-8")

    result = align(raw, annotation, manuscript)
    run = result["run"]
    seal = f"aligned_from={raw_path.name}@sha256:{_sha256(raw_path)[:12]}"
    note = run["producer"].get("note")
    run["producer"]["note"] = f"{note}; {seal}" if note else seal

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result["report"]["out"] = str(out_path)
    return result["report"]
