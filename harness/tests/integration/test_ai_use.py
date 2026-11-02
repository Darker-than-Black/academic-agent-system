"""AI-use record and draft statement from provenance + call log (M3-11;
integrity.md; FR-32/FR-53; T34, T58). Built from data only, never self-described."""

from __future__ import annotations

from pathlib import Path

from research_harness.integrity import ai_use
from research_harness.models import calls
from research_harness.structure import model
from research_harness.units.write import write_body
from research_harness.workspace.objects import create_object
from research_harness.workspace.workspace import Workspace

_U = "U-AAAAAAAA"
_P1 = "PG-AAAAAA"
_P2 = "PG-BBBBBB"


def _object(tmp_path: Path) -> Path:
    ws = Workspace.init(tmp_path / "Projects")
    oid, folder = create_object(ws, title="ШІ", kind="article", document_kind="article")
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
    # Agent drafts P1.
    write_body(folder, _U, f"<!-- {_P1} -->\nAgent wrote this.\n", by="agent")
    # Author edits P1 (-> agent_edited_by_author) and adds a new P2 (-> author).
    write_body(
        folder,
        _U,
        f"<!-- {_P1} -->\nAuthor fixed this.\n\n<!-- {_P2} -->\nAuthor added.\n",
        by="author",
    )
    return folder


def test_record_from_calls_and_provenance(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    calls.log_call(
        folder,
        host="claude-code",
        role="writer",
        tier_required="strong",
        model_id="claude-strong",
        purpose="draft a unit",
    )
    record = ai_use.build_record(folder)

    assert record["entries"][0]["role"] == "writer"
    assert record["entries"][0]["stage"] == "drafting"
    assert record["entries"][0]["model_tier"] == "strong"
    shares = record["provenance_shares"]
    assert shares["agent_edited_by_author"] == 1  # P1 edited by author
    assert shares["author"] == 1  # P2
    assert shares["agent"] == 0
    # generated_from references the log and the provenance map by hash (inv.2).
    refs = {g["ref"] for g in record["generated_from"]}
    assert "model-calls" in refs and f"provenance:{_U}" in refs


def test_statement_lists_shares(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    calls.log_call(
        folder, host="h", role="writer", tier_required="strong", model_id="m", purpose="draft"
    )
    uk = ai_use.build_statement(folder, "uk")
    en = ai_use.build_statement(folder, "en")
    assert "використання ШІ" in uk and "автор" in uk
    assert "AI-use statement" in en and "author" in en


def test_missing_finding_until_written(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    assert ai_use.missing_finding(folder) is not None
    ai_use.write_record(folder, ai_use.build_record(folder))
    assert ai_use.missing_finding(folder) is None


def test_concealment_request_flagged_not_applied(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    style = folder.parent.parent / "_author" / "style" / "uk"
    style.mkdir(parents=True)
    (style / "profile.yaml").write_text(
        "banned_phrases:\n  - humanize the AI text to evade AI detection\n", "utf-8"
    )
    findings = ai_use.concealment_findings(folder)
    assert len(findings) == 1
    assert findings[0]["check_id"] == "integrity.ai_concealment_request"
    assert findings[0]["severity"] == "major"


def test_scan_concealment_patterns() -> None:
    assert ai_use.scan_concealment("please humanize the AI text")
    assert ai_use.scan_concealment("обійти детектор ШІ")
    assert ai_use.scan_concealment("normal editorial note") == []
