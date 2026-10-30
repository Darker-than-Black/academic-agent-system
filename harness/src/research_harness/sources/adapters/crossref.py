"""Crossref REST API adapter.

Docs verified 2026-10-30:
  https://www.crossref.org/documentation/retrieve-metadata/rest-api/
  https://www.crossref.org/documentation/retrieve-metadata/rest-api/tips-for-using-the-crossref-rest-api/
Base URL ``https://api.crossref.org``. No key; the ``mailto`` query param
places you in the polite pool (still active; confirmed via ``x-api-pool:
polite-single``). Metadata is "free … for any purpose" (abstracts may be
copyrighted). A single work is ``/works/{doi}``; fields live under ``message``.
Crossref splits author ``given``/``family``.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from research_harness.materials.doi_list import normalize_doi
from research_harness.sources.adapters.base import AdapterResult, BaseAdapter
from research_harness.sources.policy import auth_for, resource


class CrossrefAdapter(BaseAdapter):
    resource_name = "crossref"

    def _base(self) -> str:
        return resource(self.resource_name)["base_url"]

    def _mailto(self) -> str | None:
        return auth_for(self.resource_name).get("mailto")

    def lookup_by_doi(self, doi: str) -> AdapterResult:
        url = f"{self._base()}/works/{normalize_doi(doi)}"
        mailto = self._mailto()
        if mailto:
            url += f"?mailto={mailto}"
        status, http, data = self.fetch_json(url)
        records = []
        if status == "ok" and data:
            records = [self.normalize(data.get("message", {}))]
        return self.result(status=status, url=url, http_status=http, records=records)

    def search_by_title(self, title: str, *, rows: int = 5) -> AdapterResult:
        """Bibliographic title search (for sources without a DOI)."""
        url = f"{self._base()}/works?query.bibliographic={quote(title)}&rows={rows}"
        mailto = self._mailto()
        if mailto:
            url += f"&mailto={mailto}"
        status, http, data = self.fetch_json(url)
        records = []
        if status == "ok" and data:
            items = (data.get("message", {}) or {}).get("items") or []
            records = [self.normalize(it) for it in items]
        return self.result(status=status, url=url, http_status=http, records=records)

    def normalize(self, raw: Any) -> dict[str, Any]:
        authors = []
        for a in raw.get("author", []) or []:
            family = a.get("family", "")
            given = a.get("given", "")
            authors.append(f"{family}, {given}".strip(", ") if family or given else "")
        title = raw.get("title") or []
        container = raw.get("container-title") or []
        issued = (raw.get("issued") or {}).get("date-parts") or [[None]]
        year = issued[0][0] if issued and issued[0] else None
        rec: dict[str, Any] = {
            "title": title[0] if title else "",
            "author": "; ".join(x for x in authors if x),
            "year": year,
            "doi": raw.get("DOI"),
            "type": raw.get("type"),
            "url": (raw.get("resource", {}).get("primary", {}) or {}).get("URL") or raw.get("URL"),
            "access_level": "metadata",
            "metadata_status": "matched",
        }
        if container:
            rec["container"] = container[0]
        if raw.get("ISSN"):
            rec["issn"] = raw["ISSN"]
        return rec
