"""Rule-pack loader and lint (02 §8.1–§8.2)."""

from __future__ import annotations

from pathlib import Path

import yaml

from research_harness.rules.loader import lint_pack, load_pack

_RULEPACKS = Path(__file__).resolve().parents[3] / "rulepacks"


def test_bundled_packs_lint_clean() -> None:
    for pid in ("core", "article", "thesis"):
        assert lint_pack(_RULEPACKS / pid) == []


def test_core_rules_are_non_overridable() -> None:
    pack = load_pack(_RULEPACKS / "core")
    assert pack.layer == 0
    assert all(r["overridable"] is False for r in pack.rules)


def test_lint_flags_core_overridable(tmp_path: Path) -> None:
    pdir = tmp_path / "bad"
    (pdir / "rules").mkdir(parents=True)
    (pdir / "pack.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "0.2",
                "id": "bad",
                "name": "bad",
                "version": "2026-10-27",
                "layer": 0,
                "status": "draft",
            }
        ),
        encoding="utf-8",
    )
    (pdir / "rules" / "r.yaml").write_text(
        yaml.safe_dump(
            [
                {
                    "id": "BAD-1",
                    "pack": "bad",
                    "version": "2026-10-27",
                    "key": "integrity.x",
                    "kind": "integrity",
                    "applies_to": ["A2"],
                    "check": ["deterministic"],
                    "severity": "major",
                    "overridable": True,
                    "statement": "x",
                    "source": {
                        "title": "t",
                        "url": "u",
                        "evidence_level": "primary",
                        "accessed_at": "2026-10-27",
                    },
                    "checked_at": "2026-10-27",
                    "valid_from": "2026-01-01",
                    "review_after": "2099-01-01",
                }
            ]
        ),
        encoding="utf-8",
    )
    problems = lint_pack(pdir)
    assert any("overridable: false" in p for p in problems)
