"""Sources & adapters (M2-01): import (T43), lookup states (T02), unavailable
resource as coverage gap (T20), retraction check, OA fetch, adapter doc notes,
no secrets in config/fixtures."""

from __future__ import annotations

import json
from pathlib import Path

from research_harness.schemas import validate
from research_harness.sources import enrich, import_files, policy, registry, retractions
from research_harness.sources.adapters import get_adapter
from research_harness.sources.transport import HttpRequest, HttpResponse
from research_harness.workspace.objects import create_object
from research_harness.workspace.workspace import Workspace
from research_harness_dev.fixtures.f4w_metadata import build_f4w_metadata

_HTTP = Path(__file__).parents[1] / "fixtures" / "http"


def _ok(name: str) -> HttpResponse:
    return HttpResponse(status=200, body=(_HTTP / name).read_bytes())


def _object(tmp_path: Path):
    ws = Workspace.init(tmp_path / "Projects")
    return create_object(ws, title="Джерела", kind="article", document_kind="article")


def _transport(req: HttpRequest) -> HttpResponse:
    u = req.url
    if "timeout" in u:
        return HttpResponse(status=None, error="timeout")
    if "api.crossref.org/works?query" in u:
        return _ok("crossref_search_two.json")
    if "api.crossref.org/works/10.7717" in u:
        return _ok("crossref_matched.json")
    if "api.crossref.org/works/10.1000/retracted" in u:
        return _ok("crossref_retracted.json")
    if "api.crossref.org/works/10.2000/clean" in u:
        return _ok("crossref_matched.json")
    if "api.crossref.org/works/10.9999" in u:
        return HttpResponse(status=404)
    if "api.openalex.org/works/" in u:
        return _ok("openalex_work.json")
    if "api.semanticscholar.org" in u:
        return HttpResponse(status=404)
    if "api.unpaywall.org" in u:
        return _ok("unpaywall_oa.json")
    if u.endswith(".pdf"):
        return HttpResponse(status=200, body=b"%PDF-1.7 synthetic open-access body\n")
    return HttpResponse(status=404)


# --- T43: Cyrillic BibTeX parsed, transliterated, sorted, duplicate linked ---
def test_import_cyrillic_bibtex(tmp_path: Path) -> None:
    _oid, folder = _object(tmp_path)
    src = build_f4w_metadata(tmp_path / "f4w") / "refs.bib"
    added, findings = import_files.import_export(folder, src, "bibtex")

    assert len(added) == 3
    for rec in added:
        assert validate("source", rec) == []  # schema-valid
    by_key = {r["bib_key"]: r for r in added}
    shev = by_key["shevchenko2024"]
    assert shev["authors"][0]["family"] == "Шевченко"
    # Preprint linked (not merged); both kept.
    pre = by_key["shevchenko2024preprint"]
    assert any(ln["relation"] == "duplicate_of" for ln in pre.get("links", []))
    assert any(f["check_id"] == "source.duplicate_unlinked" for f in findings)
    # Romanized sort: Франко (Franko) < Шевченко (Shevchenko) < Українка? sort by family.
    ordered = [
        registry.romanized_name(r["authors"][0]) for r in sorted(added, key=registry.sort_key)
    ]
    assert ordered == sorted(ordered)
    # The export file landed in the gitignored inbox, with a committed export record.
    assert (folder / "sources" / "inbox" / "refs.bib").exists()
    assert list((folder / "sources" / "exports").glob("*.json"))


# --- T02: four distinct metadata states, none becomes supported ---
def test_lookup_four_states(tmp_path: Path) -> None:
    _oid, folder = _object(tmp_path)
    import_files.import_doi_list(folder, ["10.7717/peerj.4375", "10.9999/fake", "10.5555/timeout"])
    # No-DOI-with-title and no-DOI-no-title:
    registry.add_records(folder, [{"bib_key": "amb", "title": "Assessment literacy of teachers"}])
    registry.add_records(folder, [{"bib_key": "bare"}])

    ids = [r["id"] for r in registry.load(folder)]
    enrich.lookup(folder, ids, transport=_transport)
    by_key = {r["bib_key"]: r for r in registry.load(folder)}

    assert by_key["doi1"]["metadata_status"] == "matched"
    assert by_key["doi2"]["metadata_status"] == "not_found"  # fabricated DOI (D5)
    assert by_key["doi3"]["metadata_status"] == "lookup_failed"  # timeout
    assert by_key["amb"]["metadata_status"] == "ambiguous"
    assert by_key["bare"]["metadata_status"] == "unresolved"
    # None was promoted to a support verdict by lookup.
    assert all("support" not in r for r in by_key.values())
    # Enrichment filled title/year from Crossref for the matched one.
    assert by_key["doi1"]["year"] == 2018


# --- T20: unavailable resource is a coverage gap, never "0 results" ---
def test_resource_unavailable_and_core_deferred() -> None:
    def down(_req: HttpRequest) -> HttpResponse:
        return HttpResponse(status=503)

    res = get_adapter("openalex", transport=down).lookup_by_doi("10.1/x")
    assert res.status == "unavailable" and res.records == []

    core = get_adapter("core").lookup_by_doi("10.1/x")
    assert core.status == "unavailable"  # docs unverified → deferred, not "not_found"
    assert policy.is_deferred("core")


def test_retraction_states(tmp_path: Path) -> None:
    now_clean = retractions.check_doi("10.2000/clean", transport=_transport)
    assert now_clean["status"] == "no_notice_found"
    retracted = retractions.check_doi("10.1000/retracted.1", transport=_transport)
    assert retracted["status"] == "notice_found"
    failed = retractions.check_doi("10.5555/timeout", transport=_transport)
    assert failed["status"] == "unknown"  # H7: lookup failure stays unknown, not a guess


def test_fetch_oa(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("UNPAYWALL_EMAIL", "test@example.org")
    _oid, folder = _object(tmp_path)
    added, _ = import_files.import_doi_list(folder, ["10.7717/peerj.4375"])
    sid = added[0]["id"]
    updated, findings = enrich.fetch_oa(folder, [sid], transport=_transport)
    src = registry.get(folder, sid)
    assert src["access_level"] == "fulltext"
    assert src["fulltext"]["local_path"].startswith("sources/fulltext/")
    assert src["fulltext"]["license"] == "cc-by"


def test_fetch_oa_unavailable_is_coverage_gap(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("UNPAYWALL_EMAIL", "test@example.org")
    _oid, folder = _object(tmp_path)
    added, _ = import_files.import_doi_list(folder, ["10.7717/peerj.4375"])

    def down(_req: HttpRequest) -> HttpResponse:
        return HttpResponse(status=503)

    _updated, findings = enrich.fetch_oa(folder, [added[0]["id"]], transport=down)
    assert any(f["check_id"] == "resource.unavailable" for f in findings)


# --- DoD: every adapter records a docs URL and a verification date ---
def test_adapters_have_doc_notes() -> None:
    import research_harness.sources.adapters as pkg

    adapter_dir = Path(pkg.__file__).parent
    for py in adapter_dir.glob("*.py"):
        if py.name in ("__init__.py", "base.py"):
            continue
        text = py.read_text(encoding="utf-8")
        assert "2026-10-30" in text, f"{py.name}: no verification date"
        assert "http" in text, f"{py.name}: no docs URL"


# --- H8: the policy stores only env-variable NAMES, never secret values ---
def test_policy_has_no_secret_values() -> None:
    for name, res in policy.resources().items():
        auth = res.get("auth") or {}
        for key in auth:
            assert key.endswith("_env"), f"{name}.auth.{key} is not an env-name reference"


def test_no_secret_patterns_in_fixtures() -> None:
    bad = ("Bearer ", "api_key=sk", "sk-", "Authorization:")
    for f in _HTTP.glob("*.json"):
        body = f.read_text(encoding="utf-8")
        json.loads(body)  # valid JSON
        assert not any(tok in body for tok in bad), f"{f.name}: secret-like token"
