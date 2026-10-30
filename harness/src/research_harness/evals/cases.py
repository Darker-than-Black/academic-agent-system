"""Load evaluation cases; refuse any path under holdout (H1)."""

from __future__ import annotations

from dataclasses import dataclass
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


def _check_no_holdout(nodes: list[str]) -> None:
    if any("holdout" in n for n in nodes):
        raise InvalidInputError("error.eval_holdout")


def load_suite(suite: str) -> list[Case]:
    d = CASES_DIR / suite
    if not d.is_dir():
        raise InvalidInputError("error.eval_unknown_suite")
    cases: list[Case] = []
    for f in sorted(d.glob("*.yaml")):
        data = yaml.safe_load(f.read_text(encoding="utf-8"))
        nodes = data.get("nodes", [])
        _check_no_holdout(nodes)
        cases.append(
            Case(id=data["id"], kind=data.get("kind", "pytest"), title=data["title"], nodes=nodes)
        )
    return cases
