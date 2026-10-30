"""Render an evaluation report as text (05-eval-base §8)."""

from __future__ import annotations

from typing import Any


def render_text(report: dict[str, Any]) -> str:
    lines = [
        f"Suite {report['suite']} — {report['date']}",
        f"  {report['passed']}/{report['total']} pass"
        + ("  (ALL PASS)" if report["all_pass"] else f"  ({report['failed']} FAIL)"),
        "",
    ]
    for r in report["results"]:
        mark = "pass" if r["passed"] else "FAIL"
        lines.append(f"  [{mark}] {r['id']} — {r['title']}")
        if not r["passed"]:
            lines.append(f"         {r['evidence']}")
    return "\n".join(lines) + "\n"
