"""DOAJ adapter (open-access journals and articles, venue check).

Docs verified 2026-10-30: https://doaj.org/api/docs (API v.4.0.0)
Base URL ``https://doaj.org/api``. Reads are keyless (a key is only for
publisher writes). Rate limit: 2 requests/second. Article search:
``GET /search/articles/{search_query}``; records are bibjson.
"""

from __future__ import annotations

from typing import Any

from research_harness.materials.doi_list import normalize_doi
from research_harness.sources.adapters.base import AdapterResult, BaseAdapter
from research_harness.sources.policy import resource


class DoajAdapter(BaseAdapter):
    resource_name = "doaj"

    def _base(self) -> str:
        return resource(self.resource_name)["base_url"]

    def lookup_by_doi(self, doi: str) -> AdapterResult:
        url = f"{self._base()}/search/articles/doi:{normalize_doi(doi)}"
        status, http, data = self.fetch_json(url)
        records = []
        if status == "ok" and data:
            results = data.get("results") or []
            records = [self.normalize(r.get("bibjson", {})) for r in results[:1]]
        return self.result(status=status, url=url, http_status=http, records=records)

    def normalize(self, raw: Any) -> dict[str, Any]:
        authors = [a.get("name", "") for a in raw.get("author", []) or [] if a.get("name")]
        doi = None
        issns: list[str] = []
        for ident in raw.get("identifier", []) or []:
            if ident.get("type") == "doi":
                doi = ident.get("id")
            elif ident.get("type") in ("eissn", "pissn"):
                issns.append(ident.get("id"))
        rec: dict[str, Any] = {
            "title": raw.get("title") or "",
            "author": "; ".join(authors),
            "year": raw.get("year"),
            "doi": doi,
            "access_level": "metadata",
            "metadata_status": "matched",
        }
        if (raw.get("journal") or {}).get("title"):
            rec["container"] = raw["journal"]["title"]
        if issns:
            rec["issn"] = issns
        return rec
