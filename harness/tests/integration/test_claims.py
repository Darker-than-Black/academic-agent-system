"""Claim ledger and deterministic support caps (M2-06): T06, T30 (claims part)."""

from __future__ import annotations

from pathlib import Path

from research_harness.claims import ledger as ledger_mod
from research_harness.evidence import excerpts as excerpts_mod
from research_harness.workspace.objects import create_object
from research_harness.workspace.workspace import Workspace

_UNIT = "U-ABCDEFGH"


def _object(tmp_path: Path):
    ws = Workspace.init(tmp_path / "Projects")
    return create_object(ws, title="Твердження", kind="article", document_kind="article")


def _claim(
    text: str, *, evidence=None, support="supported", materiality="material", kind="external"
):
    return {
        "text": text,
        "kind": kind,
        "materiality": materiality,
        "evidence": evidence or [],
        "support": support,
    }


def test_abstract_only_excerpt_cannot_be_supported(tmp_path: Path) -> None:  # DoD + T30
    _oid, folder = _object(tmp_path)
    exc, _ = excerpts_mod.add_excerpt(
        folder, source_id="S-0001", text="abstract line", locator={}, access_level="abstract"
    )
    stored, findings = ledger_mod.set_claims(
        folder, _UNIT, [_claim("X", evidence=[{"type": "excerpt", "id": exc["id"]}])]
    )
    assert stored[0]["support"] == "insufficient"
    assert any(f["check_id"] == "claims.support_cap_exceeded" for f in findings)


def test_source_not_found_blocks(tmp_path: Path) -> None:  # DoD
    _oid, folder = _object(tmp_path)
    stored, findings = ledger_mod.set_claims(
        folder, _UNIT, [_claim("Y", evidence=[{"type": "source", "id": "S-9999"}])]
    )
    assert stored[0]["support"] == "not_found"
    assert any(f["severity"] == "blocker" for f in findings)


def test_topic_match_without_statement_rejected(tmp_path: Path) -> None:  # DoD (N1)
    _oid, folder = _object(tmp_path)
    # Fulltext excerpt, but the quote check did not pass (no local page text).
    exc, _ = excerpts_mod.add_excerpt(
        folder, source_id="S-0002", text="some full-text line", locator={}, access_level="fulltext"
    )
    stored, findings = ledger_mod.set_claims(
        folder, _UNIT, [_claim("Z", evidence=[{"type": "excerpt", "id": exc["id"]}])]
    )
    assert stored[0]["support"] != "supported"  # never supported without a passed quote check
    assert stored[0]["support"] == "partial"
    assert any(f["check_id"] == "claims.support_cap_exceeded" for f in findings)


def test_no_evidence_is_insufficient(tmp_path: Path) -> None:
    _oid, folder = _object(tmp_path)
    stored, _ = ledger_mod.set_claims(folder, _UNIT, [_claim("no ev")])
    assert stored[0]["support"] == "insufficient"


def test_ledger_and_coverage_denominator(tmp_path: Path) -> None:  # T06 structure + coverage
    _oid, folder = _object(tmp_path)
    ledger_mod.set_claims(
        folder,
        _UNIT,
        [
            _claim("m1", materiality="material"),
            _claim("m2", materiality="critical"),
            _claim("bg", materiality="background"),
        ],
    )
    rows = ledger_mod.rebuild_ledger(folder)
    assert len(rows) == 3
    assert ledger_mod.ledger_path(folder).is_file()
    cov = ledger_mod.coverage(folder)
    assert cov["denominator"] == 2  # material + critical, not background
    assert cov["total_claims"] == 3


def test_claim_ids_and_binding(tmp_path: Path) -> None:
    _oid, folder = _object(tmp_path)
    stored, _ = ledger_mod.set_claims(folder, _UNIT, [_claim("bound")])
    c = stored[0]
    assert c["id"].startswith("C-")
    assert c["location"]["unit_id"] == _UNIT
    assert len(c["location"]["text_sha256"]) == 64
