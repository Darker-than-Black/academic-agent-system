"""Verified export re-checks every FR-12 condition in code and refuses when any
is open (M3-15; integrity.md, docx.md; T11 verified). Never trusts a cached PASS."""

from __future__ import annotations

from pathlib import Path

from research_harness.export_docx import assemble
from research_harness.gates import records as gate_records
from research_harness.integrity import ai_use, venue, verified
from research_harness.state import snapshot as snap
from research_harness.state.store import Store
from research_harness.structure import model
from research_harness.units.write import write_body
from research_harness.workspace.objects import create_object
from research_harness.workspace.workspace import Workspace

_U = "U-AAAAAAAA"
_P = "PG-AAAAAA"


def _object(tmp_path: Path) -> Path:
    ws = Workspace.init(tmp_path / "Projects")
    oid, folder = create_object(ws, title="Експорт", kind="article", document_kind="article")
    model.save(
        folder,
        {
            "schema_version": "0.2",
            "object_id": oid,
            "labels": {},
            "units": [{"id": _U, "kind": "section", "title": "Р"}],
        },
    )
    d = folder / "manuscript" / "01"
    d.mkdir(parents=True)
    (d / "text.md").write_text(f"---\nid: {_U}\ntitle: Р\nkind: section\n---\n", "utf-8")
    write_body(folder, _U, f"<!-- {_P} -->\nComplete sentence with no placeholder.\n", by="author")
    return folder


def _satisfy_all(folder: Path) -> str:
    """Make every FR-12 condition hold; return the approved snapshot id."""
    from research_harness.summaries import deterministic
    from research_harness.summaries import map as summap

    deterministic.build_unit(folder, _U)  # fresh summary so nothing is stale
    summap.build(folder)
    ai_use.write_record(folder, ai_use.build_record(folder))
    venue.record_check(
        folder,
        title="Target Journal",
        resource="scopus_sources",
        query_date="2026-11-02",
        status_value="included",
        status_date="2026-11-02",
        checked_by="author",
    )
    Store(folder).checkpoint(by="human", note="ready for verified export")
    current = snap.read_current(folder)
    gate_records.record(
        folder,
        "G3",
        decision="approved",
        reason="ready",
        target={"snapshot_id": current, "manifest_sha256": "x", "refs": []},
        channel="terminal",
    )
    return current


def test_refuses_when_conditions_open(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    findings = verified.check_conditions(folder)
    assert findings  # at least G3, AI-use, venue missing
    ids = {f["check_id"] for f in findings}
    assert "integrity.g3_invalid" in ids
    assert "integrity.ai_use_missing" in ids
    assert "integrity.venue_status" in ids


def test_g3_valid_only_for_current_snapshot(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    Store(folder).checkpoint(by="human", note="snap")
    gate_records.record(
        folder,
        "G3",
        decision="approved",
        reason="ok",
        target={"snapshot_id": "stale-snapshot", "manifest_sha256": "x", "refs": []},
        channel="terminal",
    )
    assert verified.g3_valid(folder) is False  # approval targets a different snapshot
    current = snap.read_current(folder)
    gate_records.record(
        folder,
        "G3",
        decision="approved",
        reason="ok",
        target={"snapshot_id": current, "manifest_sha256": "x", "refs": []},
        channel="terminal",
    )
    assert verified.g3_valid(folder) is True


def _validate_csl(monkeypatch, tmp_path: Path) -> None:
    """Simulate the author having validated the clean-room ДСТУ 8302:2015 CSL
    (P1-2) by pointing the pack dir at a temp copy with a validated status slot."""
    packs = tmp_path / "rulepacks"
    csl_dir = packs / "ua-fahove-b" / "csl"
    csl_dir.mkdir(parents=True)
    (csl_dir / "dstu-8302-2015.csl").write_text("<style/>", encoding="utf-8")
    (csl_dir / "dstu-8302-2015.csl.status.yaml").write_text(
        "validated: true\nvalidated_by: author\nchecked_examples: 10\n", encoding="utf-8"
    )
    monkeypatch.setattr(assemble, "_PACK_DIR", packs)


def test_unvalidated_csl_blocks_verified(tmp_path: Path) -> None:
    # P1-2 / H7: the shipped CSL is an unvalidated draft, so a verified export
    # is blocked even when every other FR-12 condition is met.
    folder = _object(tmp_path)
    _satisfy_all(folder)
    ids = {f["check_id"] for f in verified.check_conditions(folder)}
    assert "export.style_unvalidated" in ids


def test_passes_and_produces_bundle_when_all_met(tmp_path: Path, monkeypatch) -> None:
    folder = _object(tmp_path)
    current = _satisfy_all(folder)
    _validate_csl(monkeypatch, tmp_path)

    findings = verified.check_conditions(folder)
    assert findings == [], f"unexpected: {[f['check_id'] for f in findings]}"

    result = assemble.export_verified(folder, fmt="md")
    assert result["snapshot_id"] == current
    out = Path(result["dir"])
    assert out.name == f"verified-{current}"
    assert (out / "manifest.json").is_file()
    assert result["manifest"]["mode"] == "verified"
