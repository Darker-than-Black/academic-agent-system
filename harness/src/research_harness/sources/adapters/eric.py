"""ERIC adapter (education literature index; keyless).

Docs verified 2026-10-30:
  https://eric.ed.gov/?api
  https://eric.ed.gov/api/eric-api.yaml
Endpoint ``https://api.ies.ed.gov/eric/``. No API key (OpenAPI defines no
security scheme; confirmed by a keyless call). Params: ``search``, ``format``
(xml|json|csv), ``start``, ``rows`` (default 20, max 2000), ``fields``.
JSON response is ``response.docs[]``. No rate limit stated on official docs.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from research_harness.sources.adapters.base import AdapterResult, BaseAdapter
from research_harness.sources.policy import resource

_FIELDS = "id,title,author,source,publicationdateyear,issn,url,description,publicationtype"


class EricAdapter(BaseAdapter):
    resource_name = "eric"

    def _base(self) -> str:
        return resource(self.resource_name)["base_url"]

    def search(self, query: str, *, rows: int = 20) -> AdapterResult:
        url = f"{self._base()}?search={quote(query)}&format=json&rows={rows}&fields={_FIELDS}"
        status, http, data = self.fetch_json(url)
        records = []
        if status == "ok" and data:
            docs = (data.get("response") or {}).get("docs") or []
            records = [self.normalize(d) for d in docs]
        return self.result(status=status, url=url, http_status=http, records=records)

    def normalize(self, raw: Any) -> dict[str, Any]:
        authors = raw.get("author") or []
        if isinstance(authors, list):
            author = "; ".join(str(a) for a in authors)
        else:
            author = str(authors)
        rec: dict[str, Any] = {
            "title": raw.get("title") or "",
            "author": author,
            "year": raw.get("publicationdateyear"),
            "identifiers": {"eric": raw.get("id")} if raw.get("id") else {},
            "access_level": "abstract" if raw.get("description") else "metadata",
            "metadata_status": "matched",
            "type": (raw.get("publicationtype") or [None])[0]
            if isinstance(raw.get("publicationtype"), list)
            else raw.get("publicationtype"),
        }
        if raw.get("source"):
            rec["container"] = raw["source"]
        if raw.get("url"):
            url = raw["url"]
            rec["url"] = url[0] if isinstance(url, list) and url else url
        if raw.get("issn"):
            issn = raw["issn"]
            rec["issn"] = issn if isinstance(issn, list) else [issn]
        return rec
