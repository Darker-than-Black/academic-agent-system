"""Semantic Scholar Academic Graph adapter.

Docs verified 2026-10-30:
  https://www.semanticscholar.org/product/api
  https://www.semanticscholar.org/product/api/tutorial
Base URL ``https://api.semanticscholar.org/graph/v1``. API key OPTIONAL
(header ``x-api-key``; keyless public endpoints are shared-rate-limited).
Single paper by DOI: ``/paper/DOI:{doi}`` with a ``fields`` list.
``externalIds.DOI`` carries the DOI; authors are ``[{authorId, name}]``.
"""

from __future__ import annotations

from typing import Any

from research_harness.materials.doi_list import normalize_doi
from research_harness.sources.adapters.base import AdapterResult, BaseAdapter
from research_harness.sources.policy import auth_for, resource

_FIELDS = "title,year,authors,venue,publicationVenue,externalIds,abstract"


class SemanticScholarAdapter(BaseAdapter):
    resource_name = "semantic_scholar"

    def _base(self) -> str:
        return resource(self.resource_name)["base_url"]

    def _headers(self) -> dict[str, str]:
        headers = super()._headers()
        key = auth_for(self.resource_name).get("api_key")
        if key:
            headers["x-api-key"] = key
        return headers

    def lookup_by_doi(self, doi: str) -> AdapterResult:
        url = f"{self._base()}/paper/DOI:{normalize_doi(doi)}?fields={_FIELDS}"
        status, http, data = self.fetch_json(url)
        records = [self.normalize(data)] if status == "ok" and data else []
        return self.result(status=status, url=url, http_status=http, records=records)

    def normalize(self, raw: Any) -> dict[str, Any]:
        authors = [a.get("name", "") for a in raw.get("authors", []) or [] if a.get("name")]
        venue = raw.get("venue") or (raw.get("publicationVenue") or {}).get("name")
        ext = raw.get("externalIds") or {}
        rec: dict[str, Any] = {
            "title": raw.get("title") or "",
            "author": "; ".join(authors),
            "year": raw.get("year"),
            "doi": ext.get("DOI"),
            "identifiers": {"s2": raw.get("paperId")} if raw.get("paperId") else {},
            "access_level": "abstract" if raw.get("abstract") else "metadata",
            "metadata_status": "matched",
        }
        if venue:
            rec["container"] = venue
        return rec
