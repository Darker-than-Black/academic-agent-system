"""F4-W working-set builder and validator (M2-14)."""

from __future__ import annotations

from pathlib import Path

import yaml

from research_harness_dev.fixtures.check import check_f4w
from research_harness_dev.fixtures.f4w import build_f4w


def test_build_then_check_is_clean(tmp_path: Path) -> None:
    build_f4w(tmp_path)
    problems = check_f4w(tmp_path)
    hard = [p for p in problems if not p.startswith("PENDING")]
    assert hard == []  # only the annotation PENDING note remains
    assert any(p.startswith("PENDING") for p in problems)


def test_composition_and_injection(tmp_path: Path) -> None:
    build_f4w(tmp_path)
    doc = yaml.safe_load((tmp_path / "sources.yaml").read_text(encoding="utf-8"))
    srcs = doc["sources"]
    assert sum(s["lang"] == "uk" for s in srcs) == 6
    assert sum(s["lang"] == "en" for s in srcs) == 6
    assert sum(s.get("access") == "abstract" for s in srcs) == 2
    assert sum(s.get("venue_quality") == "doubtful" for s in srcs) == 1
    inj = [s for s in srcs if s.get("injection")]
    assert len(inj) == 1 and inj[0]["synthetic"] is True
    pdf = tmp_path / "injection" / "EN6-synthetic-injection.pdf"
    assert b"SYNTHETIC" in pdf.read_bytes()  # labelled, not a real paper
    # Every source has a licence and a 64-hex metadata hash.
    for s in srcs:
        assert s["license"] and len(s["metadata_sha256"]) == 64


def test_check_flags_broken_composition(tmp_path: Path) -> None:
    build_f4w(tmp_path)
    doc = yaml.safe_load((tmp_path / "sources.yaml").read_text(encoding="utf-8"))
    doc["sources"] = [s for s in doc["sources"] if s["id"] != "UA6"]  # drop one uk source
    (tmp_path / "sources.yaml").write_text(
        yaml.safe_dump(doc, allow_unicode=True), encoding="utf-8"
    )
    problems = check_f4w(tmp_path)
    assert any("composition" in p and "uk" in p for p in problems)
