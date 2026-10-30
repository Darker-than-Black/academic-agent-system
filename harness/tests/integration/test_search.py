"""Search plan, log, screening, journal, stop (M2-03): T59 (log), T61 (stop), T20."""

from __future__ import annotations

from pathlib import Path

import pytest

from research_harness.core.errors import BlockedError
from research_harness.lab import journal as journal_mod
from research_harness.lab import plan as plan_mod
from research_harness.lab import screening as screening_mod
from research_harness.lab import searchlog
from research_harness.sources.transport import HttpRequest, HttpResponse
from research_harness.workspace.objects import create_object
from research_harness.workspace.workspace import Workspace

_HTTP = Path(__file__).parents[1] / "fixtures" / "http"


def _ok(name: str) -> HttpResponse:
    return HttpResponse(status=200, body=(_HTTP / name).read_bytes())


def _object(tmp_path: Path):
    ws = Workspace.init(tmp_path / "Projects")
    return create_object(ws, title="Пошук", kind="article", document_kind="article")


def _transport(req: HttpRequest) -> HttpResponse:
    u = req.url
    if "api.ies.ed.gov" in u:
        return _ok("eric_search.json")
    if "export.arxiv.org" in u:
        return _ok("arxiv_search.xml")
    if "api.crossref.org/works?query" in u:
        return _ok("crossref_search_two.json")
    return HttpResponse(status=404)


_PLAN = {
    "question": "How does formative assessment affect achievement?",
    "resources": [
        {"resource": "eric", "queries": ["formative assessment"]},
        {"resource": "arxiv", "queries": ["formative feedback"]},
        {"resource": "crossref", "queries": ["assessment literacy"]},
    ],
    "inclusion": ["peer-reviewed"],
    "exclusion": ["non-education"],
    "saturation_rule": {"batch_size": 10, "no_new_items_in_batches": 2},
    "budget": {"max_requests": 50},
}


def test_search_without_plan_is_blocked(tmp_path: Path) -> None:
    _oid, folder = _object(tmp_path)
    with pytest.raises(BlockedError):
        searchlog.run_search(folder, "eric", "x", transport=_transport)


def test_plan_needs_stop_rule_and_budget(tmp_path: Path) -> None:
    _oid, folder = _object(tmp_path)
    bad = {"question": "q", "resources": [{"resource": "eric", "queries": ["x"]}]}
    _stored, findings = plan_mod.save_plan(folder, bad)
    assert any(f["check_id"] == "search.plan_no_stop_rule" for f in findings)
    assert plan_mod.latest_version(folder) == 0  # not saved


def test_plan_versioned(tmp_path: Path) -> None:
    _oid, folder = _object(tmp_path)
    s1, f1 = plan_mod.save_plan(folder, dict(_PLAN))
    assert s1["version"] == 1 and not any(x["severity"] == "blocker" for x in f1)
    s2, _ = plan_mod.save_plan(folder, dict(_PLAN))
    assert s2["version"] == 2 and s2["previous"] == 1


def test_log_three_adapters_and_manual_export(tmp_path: Path) -> None:  # T59 (log part)
    _oid, folder = _object(tmp_path)
    plan_mod.save_plan(folder, dict(_PLAN))
    for adapter, query in [
        ("eric", "formative assessment"),
        ("arxiv", "formative feedback"),
        ("crossref", "assessment literacy"),
    ]:
        line, added = searchlog.run_search(folder, adapter, query, transport=_transport)
        assert line["status"] == "ok" and line["records_returned"] >= 1 and added

    export = tmp_path / "scopus.ris"
    export.write_text("TY  - JOUR\nTI  - X\nER  -\n", encoding="utf-8")
    manual = searchlog.manual_log(folder, "scopus", "TITLE(assessment)", 42, export_file=export)
    assert manual["mode"] == "manual_export" and manual["export_file_sha256"]

    log = searchlog.load_log(folder)
    assert len(log) == 4
    for line in log:  # complete: query, resource, date, status, counts
        assert line["query"] and line["resource"] and line["at"] and line["status"]
        assert "records_returned" in line and line["plan_version"] == 1


def test_coverage_gap_for_unrun_resource(tmp_path: Path) -> None:  # T20
    _oid, folder = _object(tmp_path)
    plan_mod.save_plan(folder, dict(_PLAN))
    searchlog.run_search(folder, "eric", "x", transport=_transport)

    def down(_req: HttpRequest) -> HttpResponse:
        return HttpResponse(status=503)

    searchlog.run_search(folder, "openalex", "y", transport=down)
    cov = {c["resource"]: c["status"] for c in searchlog.coverage(folder)}
    assert cov["eric"] == "ok"
    assert cov["openalex"] == "unavailable"  # not "0 results"
    assert cov["doaj"] == "not_checked"  # never run


def test_stop_recorded_budget_and_saturation(tmp_path: Path) -> None:  # T61
    _oid, folder = _object(tmp_path)
    plan_mod.save_plan(folder, dict(_PLAN))
    uncovered = tmp_path / "unc.txt"
    uncovered.write_text("doaj\nscopus\n", encoding="utf-8")
    budget_stop = searchlog.record_stop(folder, "budget", ["doaj", "scopus"])
    sat_stop = searchlog.record_stop(folder, "saturation", [])
    assert budget_stop["reason"] == "budget" and budget_stop["uncovered"] == ["doaj", "scopus"]
    assert sat_stop["reason"] == "saturation"
    path = searchlog.stops_path(folder)
    assert len(path.read_text(encoding="utf-8").splitlines()) == 2


def test_screen_requires_reason(tmp_path: Path) -> None:
    _oid, folder = _object(tmp_path)
    _e, findings = screening_mod.screen(folder, "S-0001", include=False, reason="")
    assert any(f["check_id"] == "screening.decision_without_reason" for f in findings)
    e2, f2 = screening_mod.screen(folder, "S-0002", include=True, reason="on topic")
    assert e2["decision"] == "include" and not f2


def test_journal_append_only(tmp_path: Path) -> None:
    _oid, folder = _object(tmp_path)
    journal_mod.add(folder, "question", "What is the effect size?")
    journal_mod.add(folder, "dead_end", "No OA copy for S-0003", refs=["source:S-0003"])
    entries = journal_mod.load_journal(folder)
    assert len(entries) == 2 and entries[0]["kind"] == "question"
