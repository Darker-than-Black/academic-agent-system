"""Rule-pack loader and lint (02 §8.1–§8.2)."""

from __future__ import annotations

from pathlib import Path

import yaml

from research_harness.rules.loader import lint_pack, load_pack

_RULEPACKS = Path(__file__).resolve().parents[3] / "rulepacks"


def test_bundled_packs_lint_clean() -> None:
    for pid in ("core", "article", "thesis", "writing"):
        assert lint_pack(_RULEPACKS / pid) == []


def test_writing_pack_always_applies() -> None:
    # ADR-024: general writing pack has no applies_when → on for every kind.
    from research_harness.rules.selector import pack_applies

    pack = load_pack(_RULEPACKS / "writing")
    assert "applies_when" not in pack.meta
    assert pack_applies(pack, {"document_kind": "article"})
    assert pack_applies(pack, {"document_kind": "thesis"})
    assert pack_applies(pack, {})


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


def test_m3_integrity_venue_packs_lint_clean() -> None:
    # M3-23 packs: regulator integrity + venue-class rules.
    for pid in ("ua-mon-phd", "scopus-indexed", "ua-fahove-b"):
        assert lint_pack(_RULEPACKS / pid) == []


def test_ua_mon_phd_overlap_thresholds_present() -> None:
    import yaml

    data = yaml.safe_load((_RULEPACKS / "ua-mon-phd" / "overlap.yaml").read_text(encoding="utf-8"))
    assert data["shingle_size"] == 8
    assert data["min_fragment_words"] == 25
    assert data["uncited_severity"] == "blocker"


def test_scopus_venue_rule_requires_included() -> None:
    pack = load_pack(_RULEPACKS / "scopus-indexed")
    rule = next(r for r in pack.rules if r["key"] == "integrity.venue_status")
    assert rule["value"] == "included" and rule["severity"] == "blocker"
