"""Load evaluation cases; refuse any path under holdout (H1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from research_harness.core.errors import InvalidInputError

CASES_DIR = Path(__file__).resolve().parents[3] / "evals" / "cases"


@dataclass(frozen=True)
class Case:
    id: str
    kind: str
    title: str
    nodes: list[str]
    fixture: str | None = None
    metrics: list[str] = field(default_factory=list)
    inp: dict = field(default_factory=dict)
    thresholds: dict = field(default_factory=dict)


def _check_no_holdout(paths: list[str]) -> None:
    if any("holdout" in p for p in paths):
        raise InvalidInputError("error.eval_holdout")


def load_suite(suite: str) -> list[Case]:
    d = CASES_DIR / suite
    if not d.is_dir():
        raise InvalidInputError("error.eval_unknown_suite")
    cases: list[Case] = []
    for f in sorted(d.glob("*.yaml")):
        data = yaml.safe_load(f.read_text(encoding="utf-8"))
        nodes = data.get("nodes", [])
        inp = data.get("input", {}) or {}
        # H1: neither node paths nor semantic input may point under holdout.
        _check_no_holdout([*nodes, *(str(v) for v in inp.values())])
        cases.append(
            Case(
                id=data["id"],
                kind=data.get("kind", "pytest"),
                title=data["title"],
                nodes=nodes,
                fixture=data.get("fixture"),
                metrics=data.get("metric", [])
                if isinstance(data.get("metric"), list)
                else [data["metric"]]
                if data.get("metric")
                else [],
                inp=inp,
                thresholds=data.get("thresholds", {}) or {},
            )
        )
    return cases
