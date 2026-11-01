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


def parse_case(path: Path) -> Case:
    """Parse one case YAML into a Case.

    H1: a case's node paths and semantic input values must not point under
    holdout. Holdout cases themselves use package-relative paths (e.g.
    ``annotation.yaml``), so this guard does not trip on them; it still blocks a
    working-set case that reaches into holdout.
    """
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    nodes = data.get("nodes", [])
    inp = data.get("input", {}) or {}
    _check_no_holdout([*nodes, *(str(v) for v in inp.values())])
    metric = data.get("metric")
    return Case(
        id=data["id"],
        kind=data.get("kind", "pytest"),
        title=data.get("title", data["id"]),
        nodes=nodes,
        fixture=data.get("fixture"),
        metrics=metric if isinstance(metric, list) else [metric] if metric else [],
        inp=inp,
        thresholds=data.get("thresholds", {}) or {},
    )


def load_dir(d: Path) -> list[Case]:
    if not d.is_dir():
        raise InvalidInputError("error.eval_unknown_suite")
    return [parse_case(f) for f in sorted(d.glob("*.yaml"))]


def load_suite(suite: str) -> list[Case]:
    return load_dir(CASES_DIR / suite)
