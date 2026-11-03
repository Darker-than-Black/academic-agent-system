"""Post-draft substance report (ADR-023, M4-15; FR-09).

Read-only. Names, for a drafted object, which material claims are still weak and
exactly what the author must supply to raise them, plus an "analysis-free" signal
when the manuscript mostly describes the *absence* of a result. It only measures
and names deficits — it never fabricates evidence, data or a result (H6/H7), and
never fills an ``unknown`` (H7).

Not in this slice: the early readiness gate at G1, the ``article_type`` intake
field, and the semantic synthesis/scope/conclusion/consistency checks (deeper
proxies and an integration-critic follow-up). Thresholds live in the rule pack as
data; the default here mirrors ``rulepacks/ua-fahove-b/rules/substance.yaml``.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from research_harness.claims import ledger as ledger_mod
from research_harness.structure import model, ops
from research_harness.summaries.deterministic import body_of

_MATERIAL = ("critical", "material")
_WEAK = ("unreviewed", "insufficient", "not_found", "contradicted", "unverifiable")

# Default share of limitation sentences above which the manuscript reads as
# "analysis-free" (ADR-023). Mirrors the rule-pack value; data, not law.
DEFAULT_ANALYSIS_FREE_RATIO = 0.25

# What the author must supply to lift each weak support level, and why it is weak.
_REQUIRED: dict[str, tuple[str, str]] = {
    "unreviewed": (
        "no review verdict yet",
        "Run the review flow for this claim (rh review prepare → submit).",
    ),
    "insufficient": (
        "evidence does not reach 'partial'",
        "Add a fulltext excerpt with a direct quote, or soften the claim.",
    ),
    "not_found": (
        "a cited source did not resolve",
        "Resolve or replace the source, then re-extract its evidence.",
    ),
    "contradicted": (
        "the evidence contradicts the claim",
        "Reconcile the claim with the evidence, or drop it.",
    ),
    "unverifiable": (
        "cannot be verified from available sources",
        "Supply a fulltext excerpt or your own data/experiment, or demote to background.",
    ),
}

# Limitation / "could not" markers (Ukrainian), matched case-insensitively as
# substrings of a sentence.
_LIMITATION = (
    "не вдал",
    "не вийшло",
    "не дозволя",
    "не містят",
    "не вимірю",
    "недостатньо",
    "бракує",
    "не зміг",
    "неможлив",
    "відсутн",
    "не виявлено",
    "обмежен",
    "не підтвердж",
    "не встановл",
    "поза межами",
    "немає даних",
    "дані не",
)

_SENTENCE = re.compile(r"(?<=[.!?…])\s+")


def _kinds(root: Path) -> dict[str, str]:
    units = model.parse_units(model.load(root))
    out: dict[str, str] = {}

    def walk(us: Any) -> None:
        for u in us:
            out[u.id] = u.kind
            walk(u.children)

    walk(units)
    return out


def material_deficits(root: Path) -> list[dict[str, Any]]:
    """One finding per material claim whose support is still weak."""
    findings: list[dict[str, Any]] = []
    for uid in sorted({r["unit_id"] for r in ledger_mod.rebuild_ledger(root)}):
        for claim in ledger_mod.load_unit_claims(root, uid):
            if claim.get("materiality") not in _MATERIAL:
                continue
            support = claim.get("support", "unreviewed")
            if support not in _WEAK:
                continue
            why, required = _REQUIRED.get(support, ("weak support", "Strengthen the evidence."))
            cid = claim["id"]
            mat = claim.get("materiality")
            findings.append(
                {
                    "check_id": "substance.material_claim_deficit",
                    "severity": "major",
                    "reason": f"{cid} ({mat}): support {support!r} — {why}",
                    "location": {"ref": f"claim:{claim['id']}", "unit_id": uid},
                    "observed": support,
                    "proposed_action": required,
                }
            )
    return findings


def analysis_free_signal(
    root: Path, *, threshold: float = DEFAULT_ANALYSIS_FREE_RATIO
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Flag a manuscript that mostly states the absence of a result."""
    kinds = _kinds(root)
    total = 0
    limitation = 0
    for uid, folder in ops.current_folders(root).items():
        if kinds.get(uid) in ("references", "abstract"):
            continue
        tf = folder / "text.md"
        if not tf.is_file():
            continue
        body = body_of(tf.read_text(encoding="utf-8"))
        for sent in _SENTENCE.split(body):
            s = sent.strip()
            if not s:
                continue
            total += 1
            low = s.lower()
            if any(m in low for m in _LIMITATION):
                limitation += 1
    ratio = (limitation / total) if total else 0.0
    data = {"sentences": total, "limitation_sentences": limitation, "limitation_ratio": ratio}
    findings: list[dict[str, Any]] = []
    if total and ratio > threshold:
        findings.append(
            {
                "check_id": "substance.analysis_free",
                "severity": "major",
                "reason": (
                    f"{limitation}/{total} sentences ({ratio:.0%}) state a limitation or absence "
                    f"of a result (> {threshold:.0%}): the article describes the absence of a "
                    "result, not a result"
                ),
                "location": {},
                "observed": round(ratio, 3),
                "proposed_action": (
                    "Add cross-source synthesis and your own analysis, or supply the data needed "
                    "to produce a result; do not pad with more limitations."
                ),
            }
        )
    return findings, data


def build(
    root: Path, *, threshold: float = DEFAULT_ANALYSIS_FREE_RATIO
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    """Return (findings, data, next_actions) for the substance report."""
    deficits = material_deficits(root)
    af_findings, af_data = analysis_free_signal(root, threshold=threshold)
    findings = deficits + af_findings

    # Deduplicate the required inputs into author next-actions.
    seen: set[str] = set()
    next_actions: list[dict[str, Any]] = []
    for f in findings:
        action = f.get("proposed_action", "")
        if action and action not in seen:
            seen.add(action)
            next_actions.append({"who": "author", "action": action})

    data = {
        "material_claims_weak": len(deficits),
        "analysis_free": bool(af_findings),
        **af_data,
    }
    return findings, data, next_actions
