"""Retraction check via Crossref metadata (clean-room; NOT the paper-qa adoption).

Status 2026-10-30: Crossref acquired the Retraction Watch database and made it
public (GitLab CSV + the main REST API ``update-type:retraction``), but NO
explicit dataset licence (e.g. CC0) could be confirmed on any official page. Per
H7 the licence stays ``unknown``, so adoption of paper-qa's
``retractions.py`` (which downloads the Retraction Watch CSV) is POSTPONED — no
``ADP`` record is created for it (06-reuse §6 open item 1).

Instead this clean-room check uses only Crossref work metadata, which Crossref
states is "free … for any purpose". A work's ``update-to`` entries of type
``retraction`` yield ``notice_found``; a fetched record with none yields
``no_notice_found``; any lookup failure yields ``unknown`` (H7: unknown never
becomes a guess). It is conservative: absence of a Crossref retraction relation
is NOT proof a paper is not retracted, only that Crossref carries no notice.
"""

from __future__ import annotations

from typing import Any

from research_harness.core.clock import default_clock
from research_harness.materials.doi_list import normalize_doi
from research_harness.sources.policy import auth_for, resource
from research_harness.sources.transport import Transport

_RETRACTION_TYPES = {"retraction", "withdrawal", "removal"}


def _crossref_url(doi: str) -> str:
    base = resource("crossref")["base_url"]
    url = f"{base}/works/{normalize_doi(doi)}"
    mailto = auth_for("crossref").get("mailto")
    if mailto:
        url += f"?mailto={mailto}"
    return url


def check_doi(doi: str, *, transport: Transport | None = None) -> dict[str, Any]:
    """Return a ``retraction`` record ``{status, checked_at, source}`` for a DOI."""
    from research_harness.sources.adapters.crossref import CrossrefAdapter

    now = default_clock().now_rfc3339()
    adapter = CrossrefAdapter(transport=transport)
    status, _http, data = adapter.fetch_json(_crossref_url(doi))
    if status != "ok" or not data:
        return {"status": "unknown", "checked_at": now, "source": "crossref"}

    message = data.get("message", {}) or {}
    updates = message.get("update-to") or []
    for upd in updates:
        if str(upd.get("type", "")).lower() in _RETRACTION_TYPES:
            return {"status": "notice_found", "checked_at": now, "source": "crossref"}
    return {"status": "no_notice_found", "checked_at": now, "source": "crossref"}
