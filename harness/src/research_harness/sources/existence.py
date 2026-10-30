"""DOI / URL existence checks feeding ``metadata_status`` only (never support).

Adapted from opendraft-paperwriter@89128b30d9857cf9b871cbebc88ec07832260b9a
(engine/utils/citation_validator.py, MIT).
Changes: Crossref DOI lookup and URL status only; the hallucinated-citation
heuristics, the citation-database driver and the CLI report are dropped; HTTP
goes through our injectable stdlib transport (no ``requests``, no retry import);
timeout / 5xx / 429 → ``lookup_failed`` (never ``not_found``, ADR-016 p.5);
Crossref 404 → ``not_found``; 200 → ``matched``; results set ``metadata_status``
only, never ``support``. Adoption record ADP-005 (06-reuse-adoption §3.1 #31).
"""

from __future__ import annotations

from research_harness.materials.doi_list import normalize_doi
from research_harness.sources.transport import (
    HttpRequest,
    HttpResponse,
    Transport,
    is_transient,
    urllib_transport,
)

CROSSREF_WORKS = "https://api.crossref.org/works/"
_USER_AGENT = "research-harness/0.1 (https://github.com/Darker-than-Black/academic-agent-system)"
_MAX_ATTEMPTS = 3  # 1 try + 2 retries (card M2-01 step 2: retries ≤ 2)


def _headers(mailto: str | None) -> dict[str, str]:
    ua = _USER_AGENT
    if mailto:
        ua = f"{ua} mailto:{mailto}"
    return {"User-Agent": ua, "Accept": "application/json"}


def check_doi(
    doi: str,
    *,
    transport: Transport | None = None,
    mailto: str | None = None,
    timeout: float = 10.0,
) -> str:
    """Return a ``metadata_status`` for ``doi`` via Crossref.

    ``matched`` (HTTP 200), ``not_found`` (authoritative 404), or
    ``lookup_failed`` (timeout / 5xx / 429 / network after retries).
    """
    tx = transport or urllib_transport
    clean = normalize_doi(doi)
    url = f"{CROSSREF_WORKS}{clean}"
    last: HttpResponse | None = None
    for _ in range(_MAX_ATTEMPTS):
        last = tx(HttpRequest(url=url, headers=_headers(mailto), timeout=timeout))
        if not is_transient(last):
            break
    assert last is not None
    if last.status == 200:
        return "matched"
    if last.status == 404:
        return "not_found"
    return "lookup_failed"


def check_url(
    url: str,
    *,
    transport: Transport | None = None,
    timeout: float = 10.0,
) -> tuple[int | None, str]:
    """Return ``(http_status, kind)`` for a URL. ``kind`` is '', 'dead' or 'lookup_failed'.

    HEAD first; on 405 fall back to GET. 4xx/5xx with a status → ``dead``;
    transport failure → ``lookup_failed``.
    """
    tx = transport or urllib_transport
    headers = {"User-Agent": _USER_AGENT}
    resp = tx(HttpRequest(url=url, method="HEAD", headers=headers, timeout=timeout))
    if resp.status == 405:
        resp = tx(HttpRequest(url=url, method="GET", headers=headers, timeout=timeout))
    if resp.status is None:
        return None, "lookup_failed"
    if resp.status >= 400:
        return resp.status, "dead"
    return resp.status, ""
