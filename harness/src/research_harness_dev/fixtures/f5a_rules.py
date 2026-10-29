"""F5a rule packs exercising composition, freshness and caps (M1-08, T28/T29).

Synthetic (H6). Covers: a venue-class pack vs a higher journal layer; a journal
integrity rule weaker than the regulator's; an expired rule; a secondary-level
blocker; a same-layer conflict; an incomparable pair; a core override attempt.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_SRC = {
    "title": "synthetic",
    "url": "https://rh.spec/synthetic",
    "evidence_level": "primary",
    "accessed_at": "2026-10-27",
}
_SRC_SECONDARY = {**_SRC, "evidence_level": "secondary"}


def _rule(**kw: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "version": "2026-10-27",
        "applies_to": ["A2"],
        "check": ["deterministic"],
        "overridable": True,
        "statement": "synthetic rule",
        "source": _SRC,
        "checked_at": "2026-10-27",
        "valid_from": "2026-01-01",
        "review_after": "2099-01-01",
    }
    base.update(kw)
    return base


PACKS: dict[str, dict[str, Any]] = {
    "f5a-core": {
        "meta": {
            "id": "f5a-core",
            "name": "core",
            "version": "2026-10-27",
            "layer": 0,
            "status": "verified",
        },
        "rules": [
            _rule(
                id="FC-NOINVENT",
                pack="f5a-core",
                key="integrity.no_invented_evidence",
                kind="integrity",
                severity="blocker",
                overridable=False,
                compare="forbidden",
                value=True,
            ),
        ],
    },
    "f5a-regulator": {
        "meta": {
            "id": "f5a-regulator",
            "name": "regulator",
            "version": "2026-10-27",
            "layer": 3,
            "status": "verified",
            "applies_when": {"regulator": ["ua"]},
        },
        "rules": [
            _rule(
                id="FR-SELFPLAG",
                pack="f5a-regulator",
                key="integrity.selfplag",
                kind="integrity",
                severity="blocker",
                compare="min",
                value=0.9,
            ),
            _rule(
                id="FR-SECONDARY",
                pack="f5a-regulator",
                key="integrity.secondary_demo",
                kind="integrity",
                severity="blocker",
                compare="required",
                value=True,
                source=_SRC_SECONDARY,
            ),
            _rule(
                id="FR-RATIO-MIN",
                pack="f5a-regulator",
                key="integrity.ratio",
                kind="integrity",
                severity="major",
                compare="min",
                value=0.5,
            ),
        ],
    },
    "f5a-imrad": {
        "meta": {
            "id": "f5a-imrad",
            "name": "imrad",
            "version": "2026-10-27",
            "layer": 4,
            "status": "draft",
            "applies_when": {"venue_class": ["imrad"]},
        },
        "rules": [
            _rule(
                id="FI-SECTIONS",
                pack="f5a-imrad",
                key="structure.sections",
                kind="structure",
                severity="major",
                compare="one_of",
                value=["introduction", "methods", "results", "discussion"],
            ),
            _rule(
                id="FI-RATIO-MAX",
                pack="f5a-imrad",
                key="integrity.ratio",
                kind="integrity",
                severity="major",
                compare="max",
                value=0.9,
            ),
        ],
    },
    "f5a-journal": {
        "meta": {
            "id": "f5a-journal",
            "name": "journal",
            "version": "2026-10-27",
            "layer": 5,
            "status": "draft",
            "applies_when": {"venue": ["j1"]},
        },
        "rules": [
            _rule(
                id="FJ-SECTIONS",
                pack="f5a-journal",
                key="structure.sections",
                kind="structure",
                severity="major",
                compare="one_of",
                value=["narrative", "discussion"],
            ),
            _rule(
                id="FJ-SELFPLAG",
                pack="f5a-journal",
                key="integrity.selfplag",
                kind="integrity",
                severity="major",
                compare="min",
                value=0.8,
            ),
            _rule(
                id="FJ-LAYOUT",
                pack="f5a-journal",
                key="format.layout",
                kind="format",
                severity="minor",
                compare="equals",
                value="A",
            ),
        ],
    },
    "f5a-journal2": {
        "meta": {
            "id": "f5a-journal2",
            "name": "journal2",
            "version": "2026-10-27",
            "layer": 5,
            "status": "draft",
            "applies_when": {"venue": ["j1"]},
        },
        "rules": [
            _rule(
                id="FJ2-LAYOUT",
                pack="f5a-journal2",
                key="format.layout",
                kind="format",
                severity="minor",
                compare="equals",
                value="B",
            ),
        ],
    },
    "f5a-override": {
        "meta": {
            "id": "f5a-override",
            "name": "override",
            "version": "2026-10-27",
            "layer": 1,
            "status": "draft",
        },
        "rules": [
            _rule(
                id="FO-OVERRIDE",
                pack="f5a-override",
                key="integrity.no_invented_evidence",
                kind="integrity",
                severity="minor",
                compare="forbidden",
                value=False,
            ),
        ],
    },
    "f5a-expired": {
        "meta": {
            "id": "f5a-expired",
            "name": "expired",
            "version": "2026-10-27",
            "layer": 3,
            "status": "verified",
        },
        "rules": [
            _rule(
                id="FE-MINREFS",
                pack="f5a-expired",
                key="counting.min_refs",
                kind="counting",
                severity="major",
                compare="min",
                value=10,
                review_after="2000-01-01",
            ),
        ],
    },
}


def build_f5a(dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    for pid, spec in PACKS.items():
        pdir = dest / pid
        (pdir / "rules").mkdir(parents=True, exist_ok=True)
        (pdir / "pack.yaml").write_text(
            yaml.safe_dump(spec["meta"], allow_unicode=True, sort_keys=False), encoding="utf-8"
        )
        (pdir / "rules" / "rules.yaml").write_text(
            yaml.safe_dump(spec["rules"], allow_unicode=True, sort_keys=False), encoding="utf-8"
        )
    return dest


def load_f5a(dest: Path) -> list:
    from research_harness.rules.loader import load_pack

    return [load_pack(dest / pid) for pid in PACKS]
