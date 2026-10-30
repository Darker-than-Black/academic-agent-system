"""Review v0: verdict caps, coverage, integration deterministic part (M2-11)."""

from __future__ import annotations

from pathlib import Path

from research_harness.claims import ledger as ledger_mod
from research_harness.evidence import excerpts as excerpts_mod
from research_harness.review import handoff as handoff_mod
from research_harness.review import integration_v0
from research_harness.review import verdicts as verdicts_mod
from research_harness.structure import model
from research_harness.workspace.objects import create_object
from research_harness.workspace.workspace import Workspace

_U = "U-ABCDEFGH"


def _unit_object(tmp_path: Path):
    ws = Workspace.init(tmp_path / "Projects")
    _oid, folder = create_object(ws, title="Огляд", kind="article", document_kind="article")
    uf = folder / "manuscript" / "u1"
    uf.mkdir(parents=True)
    (uf / "text.md").write_text(
        f"---\nid: {_U}\ntitle: U\nkind: section\n---\nBody.\n", encoding="utf-8"
    )
    return folder


def test_verdict_exceeding_cap_is_rejected(tmp_path: Path) -> None:  # DoD deterministic
    folder = _unit_object(tmp_path)
    exc, _ = excerpts_mod.add_excerpt(
        folder, source_id="S-0001", text="abstract line", locator={}, access_level="abstract"
    )
    ledger_mod.set_claims(
        folder,
        _U,
        [
            {
                "text": "X improves Y",
                "kind": "external",
                "materiality": "material",
                "evidence": [{"type": "excerpt", "id": exc["id"]}],
                "support": "unreviewed",
            }
        ],
    )
    review = handoff_mod.prepare(folder, "unit", unit=_U)

    # Reviewer claims "supported" — cap is insufficient (abstract-only) -> rejected.
    _h, problems = verdicts_mod.submit(
        folder,
        review["id"],
        verdicts=[{"claim_id": "C-1", "support": "supported", "rationale": "topic match"}],
        findings=[],
    )
    assert any(p["check_id"] == "review.verdict_cap_exceeded" for p in problems)

    cov = verdicts_mod.coverage(folder, _U)
    assert cov["denominator"] == 1 and cov["checked"] == 0 and cov["unchecked_claims"] == ["C-1"]


def test_verdict_within_cap_is_stored_and_counted(tmp_path: Path) -> None:
    folder = _unit_object(tmp_path)
    exc, _ = excerpts_mod.add_excerpt(
        folder, source_id="S-0001", text="abstract line", locator={}, access_level="abstract"
    )
    ledger_mod.set_claims(
        folder,
        _U,
        [
            {
                "text": "X improves Y",
                "kind": "external",
                "materiality": "material",
                "evidence": [{"type": "excerpt", "id": exc["id"]}],
                "support": "unreviewed",
            }
        ],
    )
    review = handoff_mod.prepare(folder, "unit", unit=_U)
    handoff, problems = verdicts_mod.submit(
        folder,
        review["id"],
        verdicts=[{"claim_id": "C-1", "support": "insufficient", "rationale": "abstract only"}],
        findings=[],
    )
    assert not problems and handoff["status"] == "submitted"
    cov = verdicts_mod.coverage(folder, _U)
    assert cov["checked"] == 1 and cov["unchecked_claims"] == []


def test_integration_deterministic_numbers_and_crossref(tmp_path: Path) -> None:  # T22 det part
    ws = Workspace.init(tmp_path / "Projects")
    _oid, folder = create_object(ws, title="Інтеграція", kind="article", document_kind="article")
    model.save(
        folder,
        {
            "schema_version": "0.2",
            "object_id": _oid,
            "labels": {},
            "units": [
                {"id": "U-AAAAAAAA", "kind": "abstract", "title": "Abstract"},
                {"id": "U-BBBBBBBB", "kind": "section", "title": "Body"},
            ],
        },
    )
    (folder / "manuscript" / "abs").mkdir(parents=True)
    (folder / "manuscript" / "sec").mkdir(parents=True)
    (folder / "manuscript" / "abs" / "text.md").write_text(
        "---\nid: U-AAAAAAAA\ntitle: Abstract\nkind: abstract\n---\nEffect was 42 percent.\n",
        encoding="utf-8",
    )
    (folder / "manuscript" / "sec" / "text.md").write_text(
        "---\nid: U-BBBBBBBB\ntitle: Body\nkind: section\n---\n"
        "We saw 7 cases. See {{ref:U-ZZZZZZZZ}}.\n",
        encoding="utf-8",
    )
    findings = integration_v0.check(folder)
    ids = {f["check_id"] for f in findings}
    assert "integration.number_not_in_body" in ids  # 42 not in body
    assert "integration.cross_ref_unresolved" in ids  # U-ZZZZZZZZ missing
