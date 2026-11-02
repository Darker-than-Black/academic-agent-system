"""M3-22 fixtures feed their intended checks (synthetic, H6).

F5c → prompt-injection (T14/D10); F5g → venue status (T39/D14); F8 → tuple
validator (T05-tuple); F7-defects → fulltext crossref (D18) + repeated fragment
(D16)."""

from __future__ import annotations

import json
from pathlib import Path

from research_harness.analysis import rows as rows_mod
from research_harness.analysis import tuples as tuples_mod
from research_harness.integrity import injection as injection_mod
from research_harness.integrity import venue as venue_mod
from research_harness.review import fulltext as fulltext_mod
from research_harness_dev.fixtures.f5c_injection import build_f5c
from research_harness_dev.fixtures.f5g_venue import build_f5g
from research_harness_dev.fixtures.f7_structure import build_f7_defects
from research_harness_dev.fixtures.f8_analysis import ROW_ID, build_f8


def test_f5c_triggers_injection_scan(tmp_path: Path) -> None:
    dest = build_f5c(tmp_path / "f5c")
    text = (dest / "injection-sample.md").read_text(encoding="utf-8")
    names = {f["observed"] for f in injection_mod.scan(text, location={"ref": "f5c"})}
    findings = injection_mod.scan(text)
    assert all(f["check_id"] == "integrity.prompt_injection" for f in findings)
    # English imperative, Ukrainian imperative and the token URL are all caught.
    assert len(findings) >= 3 and any("api_key=" in o for o in names)


def test_f5g_venue_status_unknown_and_not_included(tmp_path: Path) -> None:
    dest = build_f5g(tmp_path / "f5g")
    checks = venue_mod.list_checks(dest)
    values = {c["status_on_date"]["value"] for c in checks}
    assert "unknown" in values and "not_included" in values
    # The latest recorded check drives integrity.venue_status (blocks verified export).
    assert any(f["check_id"] == "integrity.venue_status" for f in venue_mod.status_findings(dest))


def test_f8_tuple_validator_flags_scale_defect(tmp_path: Path) -> None:
    dest = build_f8(tmp_path / "f8")
    rows_by_id = rows_mod.by_id(dest)
    assert ROW_ID in rows_by_id
    claims = json.loads((dest / "manuscript" / "claims.json").read_text("utf-8"))["claims"]
    by_id = {c["id"]: c for c in claims}
    assert tuples_mod.check_claim(by_id["CL-OK"], rows_by_id) == []
    bad = tuples_mod.check_claim(by_id["CL-SCALE"], rows_by_id)
    assert any(f["check_id"] == "analysis.implicit_conversion" for f in bad)


def test_f7_defects_crossref_and_repeat(tmp_path: Path) -> None:
    folder = build_f7_defects(tmp_path / "f7d")
    findings = fulltext_mod.run(folder)
    ids = {f["check_id"] for f in findings}
    assert "fulltext.crossref" in ids  # D18
    assert "fulltext.repeated_fragment" in ids  # D16
