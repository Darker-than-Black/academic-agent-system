"""Render an evaluation report as text (05-eval-base §8)."""

from __future__ import annotations

from typing import Any


def render_text(report: dict[str, Any]) -> str:
    pend = report.get("pending", 0)
    head = (
        f"  {report['passed']}/{report['total']} pass"
        + ("  (ALL PASS)" if report["all_pass"] else f"  ({report['failed']} FAIL)")
        + (f"  [{pend} pending]" if pend else "")
    )
    lines = [f"Suite {report['suite']} — {report['date']}", head, ""]
    for r in report["results"]:
        mark = "pend" if r.get("pending") else ("pass" if r["passed"] else "FAIL")
        lines.append(f"  [{mark}] {r['id']} — {r['title']}")
        if r.get("run_kind"):
            tag = " — SYNTHETIC, not a gate baseline" if r["run_kind"] == "synthetic" else ""
            lines.append(f"         run: {r['run_kind']}{tag}")
        if r.get("metrics"):
            for name, m in r["metrics"].items():
                lines.append(f"         {_metric_line(name, m)}")
        if r.get("pending") or not r["passed"]:
            lines.append(f"         {r['evidence']}")
    return "\n".join(lines) + "\n"


def _ci(d: dict[str, Any]) -> str:
    return f"{d['value']:.3f} (n={d['n']}, 95% CI {d['lo']:.3f}–{d['hi']:.3f})"


def _metric_line(name: str, m: dict[str, Any]) -> str:
    if name == "MX":
        return f"MX recall {_ci(m['recall'])}; precision {_ci(m['precision'])}"
    if name == "MV":
        return (
            f"MV accuracy {_ci(m['accuracy'])}; macro-F1 {m['macro_f1']:.3f}; "
            f"critical recall {_ci(m['critical_recall'])}"
        )
    if name == "MS":
        miss = ",".join(m["missed_defects"]) or "none"
        return f"MS recall {_ci(m['recall'])}; precision {_ci(m['precision'])}; missed {miss}"
    if name == "MF":
        return (
            f"MF false PASS {m['false_pass']} (critical {m['critical_false_pass']}, "
            f"target {'met' if m['critical_target_met'] else 'MISSED'})"
        )
    if name == "MA":
        met = "met" if m["target_met"] else "MISSED"
        return f"MA invented {m['invented']}/{m['n']} (target {met})"
    return f"{name}: {m}"
