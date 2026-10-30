"""arXiv adapter (preprints; keyless, Atom XML).

Docs verified 2026-10-30:
  https://info.arxiv.org/help/api/user-manual.html
  https://info.arxiv.org/help/api/tou.html
Endpoint ``https://export.arxiv.org/api/query``. No API key. ToU: "make no more
than one request every three seconds" and a single connection at a time. The
body is "Atom 1.0". Entry fields: ``title``, ``author/name``, ``published``
(year), ``arxiv:doi`` (only if the author supplied one), ``summary`` (abstract).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import quote

from research_harness.sources.adapters.base import AdapterResult, BaseAdapter, _status_for
from research_harness.sources.policy import resource

_ATOM = "{http://www.w3.org/2005/Atom}"
_ARXIV = "{http://arxiv.org/schemas/atom}"


class ArxivAdapter(BaseAdapter):
    resource_name = "arxiv"

    def _base(self) -> str:
        return resource(self.resource_name)["base_url"]

    def search(self, query: str, *, max_results: int = 20) -> AdapterResult:
        url = f"{self._base()}?search_query={quote(query)}&max_results={max_results}"
        resp = self.fetch(url)
        status = _status_for(resp)
        records: list[dict[str, Any]] = []
        if status == "ok":
            try:
                root = ET.fromstring(resp.body.decode("utf-8"))  # noqa: S314 - arXiv, our transport
                records = [self.normalize(e) for e in root.findall(f"{_ATOM}entry")]
            except ET.ParseError:
                status = "lookup_failed"
        return self.result(status=status, url=url, http_status=resp.status, records=records)

    def normalize(self, raw: Any) -> dict[str, Any]:
        entry: ET.Element = raw
        title_el = entry.find(f"{_ATOM}title")
        summary_el = entry.find(f"{_ATOM}summary")
        published_el = entry.find(f"{_ATOM}published")
        id_el = entry.find(f"{_ATOM}id")
        doi_el = entry.find(f"{_ARXIV}doi")
        authors = [
            (n.text or "").strip()
            for a in entry.findall(f"{_ATOM}author")
            if (n := a.find(f"{_ATOM}name")) is not None
        ]
        year = None
        if published_el is not None and published_el.text:
            year = published_el.text[:4]
        rec: dict[str, Any] = {
            "title": " ".join((title_el.text or "").split()) if title_el is not None else "",
            "author": "; ".join(a for a in authors if a),
            "year": year,
            "type": "preprint",
            "identifiers": {"arxiv": id_el.text} if id_el is not None and id_el.text else {},
            "access_level": "abstract" if summary_el is not None else "metadata",
            "metadata_status": "matched",
        }
        if id_el is not None and id_el.text:
            rec["url"] = id_el.text
        if doi_el is not None and doi_el.text:
            rec["doi"] = doi_el.text.strip()
        return rec
