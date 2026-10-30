"""OpenAlex adapter.

Docs verified 2026-10-30:
  https://help.openalex.org/how-to-use-the-api/api-overview
  https://help.openalex.org/api/authentication/
  https://help.openalex.org/api/deprecations/
Base URL ``https://api.openalex.org``. API key OPTIONAL (passed as ``api_key``
query param; keyless works). VERIFIED CHANGE: the ``mailto`` "polite pool" was
removed by OpenAlex in Feb 2026 and ``mailto`` is now ignored — this adapter
does NOT send it. Data is CC0. Author objects expose ``display_name`` /
``raw_author_name`` only (no given/family split).
"""

from __future__ import annotations

from typing import Any

from research_harness.materials.doi_list import normalize_doi
from research_harness.sources.adapters.base import AdapterResult, BaseAdapter
from research_harness.sources.policy import auth_for, resource


class OpenAlexAdapter(BaseAdapter):
    resource_name = "openalex"

    def _base(self) -> str:
        return resource(self.resource_name)["base_url"]

    def _url(self, path: str) -> str:
        url = f"{self._base()}{path}"
        key = auth_for(self.resource_name).get("api_key")
        if key:
            url += ("&" if "?" in url else "?") + f"api_key={key}"
        return url

    def lookup_by_doi(self, doi: str) -> AdapterResult:
        url = self._url(f"/works/https://doi.org/{normalize_doi(doi)}")
        status, http, data = self.fetch_json(url)
        records = [self.normalize(data)] if status == "ok" and data else []
        return self.result(status=status, url=url, http_status=http, records=records)

    def normalize(self, raw: Any) -> dict[str, Any]:
        authors = []
        for a in raw.get("authorships", []) or []:
            author = a.get("author", {}) or {}
            name = a.get("raw_author_name") or author.get("display_name")
            if name:
                authors.append(name)
        oa = raw.get("open_access", {}) or {}
        best = raw.get("best_oa_location") or {}
        primary = raw.get("primary_location") or {}
        container = (primary.get("source") or {}).get("display_name")
        rec: dict[str, Any] = {
            "title": raw.get("title") or raw.get("display_name") or "",
            "author": "; ".join(authors),
            "year": raw.get("publication_year"),
            "doi": raw.get("doi"),
            "type": raw.get("type"),
            "identifiers": {"openalex": raw.get("id")} if raw.get("id") else {},
            "access_level": "metadata",
            "metadata_status": "matched",
        }
        if container:
            rec["container"] = container
        oa_pdf = best.get("pdf_url") or oa.get("oa_url")
        if oa_pdf:
            rec["oa_pdf_url"] = oa_pdf
            rec["oa_status"] = oa.get("oa_status")
        return rec
