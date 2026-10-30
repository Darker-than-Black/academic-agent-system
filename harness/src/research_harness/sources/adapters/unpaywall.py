"""Unpaywall adapter (OA status and legal OA full-text locations).

Docs verified 2026-10-30: https://unpaywall.org/products/api
Base URL ``https://api.unpaywall.org/v2``. No key; an ``email`` query param is
REQUIRED on every request. Single DOI: ``GET /v2/{doi}?email=…``. The OA PDF is
``best_oa_location.url_for_pdf`` (fall back to ``oa_locations[]``). Authors are
in ``z_authors`` (shape varies: ``given``/``family`` or ``raw_author_name``).
"""

from __future__ import annotations

from typing import Any

from research_harness.materials.doi_list import normalize_doi
from research_harness.sources.adapters.base import AdapterResult, BaseAdapter
from research_harness.sources.policy import auth_for, resource


class UnpaywallAdapter(BaseAdapter):
    resource_name = "unpaywall"

    def _base(self) -> str:
        return resource(self.resource_name)["base_url"]

    def lookup_by_doi(self, doi: str) -> AdapterResult:
        email = auth_for(self.resource_name).get("email")
        if not email:
            # email is mandatory; without it we never call (NFR-06). Report as blocked.
            url = f"{self._base()}/{normalize_doi(doi)}"
            return self.result(status="blocked", url=url, http_status=None, records=[])
        url = f"{self._base()}/{normalize_doi(doi)}?email={email}"
        status, http, data = self.fetch_json(url)
        records = [self.normalize(data)] if status == "ok" and data else []
        return self.result(status=status, url=url, http_status=http, records=records)

    def normalize(self, raw: Any) -> dict[str, Any]:
        authors = []
        for a in raw.get("z_authors", []) or []:
            name = a.get("raw_author_name")
            if not name:
                family = a.get("family", "")
                given = a.get("given", "")
                name = f"{family}, {given}".strip(", ")
            if name:
                authors.append(name)
        best = raw.get("best_oa_location") or {}
        if not best:
            locs = raw.get("oa_locations") or []
            best = locs[0] if locs else {}
        rec: dict[str, Any] = {
            "title": raw.get("title") or "",
            "author": "; ".join(authors),
            "year": raw.get("year"),
            "doi": raw.get("doi"),
            "access_level": "metadata",
            "metadata_status": "matched",
        }
        if raw.get("journal_name"):
            rec["container"] = raw["journal_name"]
        if raw.get("journal_issns"):
            rec["issn"] = [s.strip() for s in str(raw["journal_issns"]).split(",") if s.strip()]
        pdf = best.get("url_for_pdf") or best.get("url")
        if pdf:
            rec["oa_pdf_url"] = pdf
            rec["oa_status"] = raw.get("oa_status")
            rec["oa_version"] = best.get("version")
            rec["oa_license"] = best.get("license")
        return rec
