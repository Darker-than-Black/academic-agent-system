"""Semantic evaluation metrics (05-eval-base §6), core and LLM-free (H5).

Each scorer takes the reference annotation (``annotation.yaml`` as a dict, §5.1)
and a *run artifact* (the model output, ``eval_run`` schema) and returns a
deterministic result. The run artifact is produced outside the core — by host
subagents on a semantic run (С) — and fed in as JSON; nothing here calls a model.

Metrics: MX (claim extraction recall/precision), MV (verdict precision/recall,
macro-F1, critical recall), MS (seeded-defect recall/precision), MF (false PASS,
= 0 for critical), MA (contribution points: no invented position). Proportions
carry n and a 95% Wilson confidence interval; a value without n and CI is not
accepted at a gate (§6).
"""

from __future__ import annotations

import math
from typing import Any

Z95 = 1.959963984540054


def wilson(k: int, n: int, z: float = Z95) -> dict[str, float | int]:
    """95% Wilson score interval for k successes out of n."""
    if n == 0:
        return {"value": 0.0, "n": 0, "lo": 0.0, "hi": 0.0}
    p = k / n
    z2 = z * z
    denom = 1 + z2 / n
    centre = (p + z2 / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))) / denom
    return {
        "value": round(p, 4),
        "n": n,
        "k": k,
        "lo": round(max(0.0, centre - half), 4),
        "hi": round(min(1.0, centre + half), 4),
    }


def _gold_index(annotation: dict[str, Any]) -> dict[str, dict]:
    return {c["claim_id"]: c for c in annotation.get("claims", [])}


# ---- MX: claim extraction recall / precision ----------------------------------
def score_mx(annotation: dict, run: dict) -> dict:
    gold = _gold_index(annotation)
    gold_material = {cid for cid, c in gold.items() if c.get("material")}
    extracted = run.get("extracted", [])
    hit_ids = {e["claim_id"] for e in extracted if e.get("claim_id") in gold_material}
    # precision denominator: every extracted item claiming to be material
    extracted_material = [e for e in extracted if e.get("material", True)]
    tp = len({e["claim_id"] for e in extracted_material if e.get("claim_id") in gold_material})
    recall = wilson(len(hit_ids), len(gold_material))
    precision = (
        wilson(tp, len(extracted_material))
        if extracted_material
        else {"value": 0.0, "n": 0, "lo": 0.0, "hi": 0.0}
    )
    return {"metric": "MX", "recall": recall, "precision": precision}


# ---- MV: verdict accuracy -----------------------------------------------------
_CLASSES = ["supported", "partial", "insufficient", "contradicted", "not_found", "unverifiable"]


def score_mv(annotation: dict, run: dict) -> dict:
    gold = _gold_index(annotation)
    pred = {r["claim_id"]: r.get("verdict") for r in run.get("reviewed", [])}
    scored = [
        (cid, g["expected_verdict"], pred[cid])
        for cid, g in gold.items()
        if cid in pred and g.get("expected_verdict")
    ]
    n = len(scored)
    per_class: dict[str, dict] = {}
    f1s = []
    for cls in _CLASSES:
        tp = sum(1 for _, y, p in scored if y == cls and p == cls)
        fp = sum(1 for _, y, p in scored if y != cls and p == cls)
        fn = sum(1 for _, y, p in scored if y == cls and p != cls)
        support = sum(1 for _, y, _ in scored if y == cls)
        if support == 0 and tp + fp == 0:
            continue
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        per_class[cls] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "support": support,
        }
        if support:
            f1s.append(f1)
    macro_f1 = round(sum(f1s) / len(f1s), 4) if f1s else 0.0
    # critical recall: exact-verdict match on critical claims
    crit = [(y, p) for cid, y, p in scored if gold[cid].get("criticality") == "critical"]
    crit_rec = wilson(sum(1 for y, p in crit if y == p), len(crit))
    acc = wilson(sum(1 for _, y, p in scored if y == p), n)
    return {
        "metric": "MV",
        "n": n,
        "accuracy": acc,
        "macro_f1": macro_f1,
        "per_class": per_class,
        "critical_recall": crit_rec,
    }


# ---- MS: seeded-defect recall / precision -------------------------------------
def score_ms(annotation: dict, run: dict) -> dict:
    gold = _gold_index(annotation)
    # gold defects: one per claim with defect_id, plus integration findings (D13 etc.)
    gold_defects = {cid: c["defect_id"] for cid, c in gold.items() if c.get("defect_id")}
    integ = annotation.get("expected_integration_findings", [])
    gold_integ = {f.get("id", f["defect_id"]): f["defect_id"] for f in integ if f.get("defect_id")}

    flagged = {r["claim_id"]: set(r.get("flagged_defects", [])) for r in run.get("reviewed", [])}
    run_integ = {
        f.get("defect_id") for f in run.get("integration_findings", []) if f.get("defect_id")
    }

    caught = 0
    for cid, did in gold_defects.items():
        if did in flagged.get(cid, set()):
            caught += 1
    for _fid, did in gold_integ.items():
        if did in run_integ:
            caught += 1
    total = len(gold_defects) + len(gold_integ)
    recall = wilson(caught, total)

    # precision: flagged defects that match the gold defect on that claim
    total_flags = sum(len(s) for s in flagged.values()) + len(run_integ)
    correct_flags = sum(
        1 for cid, s in flagged.items() if cid in gold_defects and gold_defects[cid] in s
    )
    correct_flags += sum(1 for did in run_integ if did in set(gold_integ.values()))
    precision = (
        wilson(correct_flags, total_flags)
        if total_flags
        else {"value": 0.0, "n": 0, "lo": 0.0, "hi": 0.0}
    )
    missed = sorted(did for cid, did in gold_defects.items() if did not in flagged.get(cid, set()))
    missed += sorted(did for did in gold_integ.values() if did not in run_integ)
    return {"metric": "MS", "recall": recall, "precision": precision, "missed_defects": missed}


# ---- MF: false PASS -----------------------------------------------------------
def score_mf(annotation: dict, run: dict) -> dict:
    gold = _gold_index(annotation)
    pred = {r["claim_id"]: r.get("verdict") for r in run.get("reviewed", [])}
    false_pass = [
        cid
        for cid, g in gold.items()
        if pred.get(cid) == "supported" and g.get("expected_verdict") not in (None, "supported")
    ]
    critical_fp = [cid for cid in false_pass if gold[cid].get("criticality") == "critical"]
    return {
        "metric": "MF",
        "false_pass": len(false_pass),
        "false_pass_claims": false_pass,
        "critical_false_pass": len(critical_fp),
        "critical_false_pass_claims": critical_fp,
        "critical_target_met": len(critical_fp) == 0,
    }


# ---- MA: author contribution points (no invented position) --------------------
def score_ma(annotation: dict, run: dict) -> dict:
    points = run.get("contribution_points", [])
    invented = [p["point_id"] for p in points if p.get("response") == "invented"]
    return {
        "metric": "MA",
        "n": len(points),
        "invented": len(invented),
        "invented_points": invented,
        "target_met": len(invented) == 0,
    }


SCORERS = {"MX": score_mx, "MV": score_mv, "MS": score_ms, "MF": score_mf, "MA": score_ma}


def score(metric: str, annotation: dict, run: dict) -> dict:
    if metric not in SCORERS:
        raise ValueError(f"unknown metric {metric!r}")
    return SCORERS[metric](annotation, run)
