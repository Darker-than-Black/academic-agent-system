"""Article integration review v0 — deterministic part (CLI). The semantic part
is the integration-critic role (M3). FR-22.

Checks: every number in the abstract appears somewhere in the body; glossary
terms are consistent; cross-references resolve. No "PASS" wording.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from research_harness.structure import model, ops
from research_harness.summaries import glossary as glossary_mod
from research_harness.summaries.deterministic import body_of

_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
_CROSSREF = re.compile(r"\{\{ref:(U-[0-9A-HJKMNP-TV-Z]{8})\}\}")


def _kinds(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}

    def walk(nodes):
        for n in nodes:
            out[n.id] = n.kind
            walk(n.children)

    walk(model.parse_units(model.load(root)))
    return out


def _body(folder: Path) -> str:
    return body_of((folder / "text.md").read_text(encoding="utf-8"))


def check(root: Path) -> list[dict[str, Any]]:
    folders = ops.current_folders(root)
    kinds = _kinds(root)
    findings: list[dict[str, Any]] = []

    bodies = {uid: _body(f) for uid, f in folders.items()}
    abstract_ids = [uid for uid, k in kinds.items() if k == "abstract" and uid in bodies]
    body_numbers: set[str] = set()
    for uid, body in bodies.items():
        if uid not in abstract_ids:
            body_numbers |= set(_NUMBER.findall(body))

    for uid in abstract_ids:
        for num in set(_NUMBER.findall(bodies[uid])):
            if num not in body_numbers:
                findings.append(
                    _f(
                        "integration.number_not_in_body",
                        "major",
                        f"abstract number {num!r} appears in no body unit",
                    )
                )

    known = set(folders)
    for uid, body in bodies.items():
        for ref in _CROSSREF.findall(body):
            if ref not in known:
                findings.append(
                    _f(
                        "integration.cross_ref_unresolved",
                        "major",
                        f"{uid}: cross-reference {ref!r} resolves to no unit",
                    )
                )

    findings.extend(glossary_mod.check(root))
    return findings


def _f(check_id: str, severity: str, reason: str) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "severity": severity,
        "reason": reason,
        "location": {},
        "proposed_action": "",
    }
