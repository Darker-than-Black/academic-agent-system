"""Source enrichment: ``rh source lookup`` and ``rh source fetch-oa`` logic.

``lookup`` resolves each source's ``metadata_status`` deterministically and
merges metadata without inventing anything (H6):
  * DOI present → Crossref existence check: 200 → ``matched`` (+ enrich);
    404 → ``not_found`` (blocker for citing, D5); timeout/5xx/429 →
    ``lookup_failed`` (never ``not_found``, ADR-016).
  * no DOI but a title → Crossref title search: 1 hit → ``matched``;
    >1 → ``ambiguous``; 0 → ``not_found``.
  * neither → stays ``unresolved``.
Support is never set here (that is the claim ledger / critic, M2-06/M2-11).

``fetch_oa`` resolves a legal OA location via Unpaywall and, when a transport
returns the bytes, stores the full text under ``sources/fulltext/`` (gitignored)
with license and version; otherwise it records the resolved OA URL as data.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from research_harness.core.clock import default_clock
from research_harness.core.hashing import file_hash
from research_harness.sources import existence, registry
from research_harness.sources.adapters import get_adapter
from research_harness.sources.policy import auth_for, is_api, is_deferred
from research_harness.sources.transport import Transport

# Default enrichment adapters, in order (DOI-capable), excluding deferred ones.
_DEFAULT_ENRICH = ("crossref", "openalex", "semantic_scholar")
_MERGE_FIELDS = ("title", "year", "container", "url", "issn", "type", "identifiers")


def _finding(check_id: str, severity: str, sid: str, reason: str) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "severity": severity,
        "reason": reason,
        "location": {"ref": f"source:{sid}"},
        "proposed_action": "",
    }


def _merge(source: dict[str, Any], rec: dict[str, Any]) -> None:
    """Fill only missing/empty fields of ``source`` from a normalized record."""
    for field in _MERGE_FIELDS:
        val = rec.get(field)
        if val and not source.get(field):
            source[field] = val
    if rec.get("author") and not source.get("authors"):
        source["authors"] = registry.parse_authors(rec["author"])
    if rec.get("access_level") == "abstract" and source.get("access_level") == "metadata":
        source["access_level"] = "abstract"


def lookup(
    root: Path,
    source_ids: list[str],
    *,
    adapters: tuple[str, ...] = _DEFAULT_ENRICH,
    transport: Transport | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    updated: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    active = [a for a in adapters if is_api(a) and not is_deferred(a)]
    mailto = auth_for("crossref").get("mailto")

    for sid in source_ids:
        source = registry.get(root, sid)
        if source is None:
            raise KeyError(sid)
        doi = source.get("doi")
        meta_src = source.setdefault("metadata_sources", [])

        if doi:
            status = existence.check_doi(doi, transport=transport, mailto=mailto)
            source["metadata_status"] = status
            if status == "matched":
                _enrich(source, doi, active, transport, meta_src)
            elif status == "not_found":
                findings.append(
                    _finding("source.not_found", "blocker", sid, f"DOI not found: {doi}")
                )
            elif status == "lookup_failed":
                findings.append(
                    _finding("source.lookup_failed", "minor", sid, f"DOI lookup failed: {doi}")
                )
        elif source.get("title"):
            status = _title_lookup(source, active, transport, meta_src)
            source["metadata_status"] = status
            if status == "ambiguous":
                findings.append(
                    _finding("source.metadata_unresolved", "minor", sid, "multiple title matches")
                )
            elif status == "not_found":
                findings.append(_finding("source.not_found", "blocker", sid, "no title match"))
        else:
            source["metadata_status"] = "unresolved"
            findings.append(
                _finding("source.metadata_unresolved", "minor", sid, "no DOI and no title")
            )

        registry.update(root, sid, source)
        updated.append(source)
    return updated, findings


def _enrich(
    source: dict[str, Any],
    doi: str,
    adapters: list[str],
    transport: Transport | None,
    meta_src: list[dict[str, Any]],
) -> None:
    now = default_clock().now_rfc3339()
    for name in adapters:
        try:
            res = get_adapter(name, transport=transport).lookup_by_doi(doi)
        except NotImplementedError:
            continue
        if res.ok and res.records:
            _merge(source, res.records[0])
            meta_src.append(
                {"resource": name, "record_id": res.request["params_hash"], "retrieved_at": now}
            )


def _title_lookup(
    source: dict[str, Any],
    adapters: list[str],
    transport: Transport | None,
    meta_src: list[dict[str, Any]],
) -> str:
    from research_harness.sources.adapters.crossref import CrossrefAdapter

    res = CrossrefAdapter(transport=transport).search_by_title(source["title"])
    if not res.ok:
        return "lookup_failed" if res.status == "lookup_failed" else "unresolved"
    hits = res.records
    if len(hits) == 1:
        _merge(source, hits[0])
        if hits[0].get("doi"):
            source["doi"] = hits[0]["doi"]
        meta_src.append(
            {
                "resource": "crossref",
                "record_id": res.request["params_hash"],
                "retrieved_at": default_clock().now_rfc3339(),
            }
        )
        return "matched"
    if len(hits) > 1:
        return "ambiguous"
    return "not_found"


def fetch_oa(
    root: Path,
    source_ids: list[str],
    *,
    transport: Transport | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Resolve and (if bytes available) store a legal OA full text per source."""
    updated: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    fulltext_dir = root / "sources" / "fulltext"

    for sid in source_ids:
        source = registry.get(root, sid)
        if source is None:
            raise KeyError(sid)
        doi = source.get("doi")
        if not doi:
            findings.append(_finding("source.metadata_unresolved", "minor", sid, "no DOI for OA"))
            continue
        res = get_adapter("unpaywall", transport=transport).lookup_by_doi(doi)
        if not res.ok or not res.records:
            findings.append(
                _finding("resource.unavailable", "info", sid, f"unpaywall: {res.status}")
            )
            continue
        rec = res.records[0]
        oa_url = rec.get("oa_pdf_url")
        if not oa_url:
            findings.append(_finding("source.access_abstract_only", "info", sid, "no OA full text"))
            registry.update(root, sid, source)
            updated.append(source)
            continue
        source.setdefault("identifiers", {})["oa_pdf_url"] = oa_url
        _download_oa(source, oa_url, rec, fulltext_dir, sid, transport)
        registry.update(root, sid, source)
        updated.append(source)
    return updated, findings


def _download_oa(
    source: dict[str, Any],
    oa_url: str,
    rec: dict[str, Any],
    fulltext_dir: Path,
    sid: str,
    transport: Transport | None,
) -> None:
    from research_harness.sources.transport import HttpRequest, urllib_transport

    tx = transport or urllib_transport
    resp = tx(HttpRequest(url=oa_url, headers={"User-Agent": "research-harness/0.1"}))
    if resp.status != 200 or not resp.body:
        return
    fulltext_dir.mkdir(parents=True, exist_ok=True)
    dest = fulltext_dir / f"{sid}.pdf"
    dest.write_bytes(resp.body)
    source["access_level"] = "fulltext"
    source["fulltext"] = {
        "local_path": dest.relative_to(fulltext_dir.parent.parent).as_posix(),
        "sha256": file_hash(dest),
        "version": rec.get("oa_version") or "unknown",
        "obtained_via": "unpaywall",
    }
    if rec.get("oa_license"):
        source["fulltext"]["license"] = rec["oa_license"]
