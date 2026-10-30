"""Acceptance test for ADP-004 (OpenDraft citation_validator adaptation).

DOI existence maps to our metadata_status, never to support: 200 → matched,
404 → not_found, transient (timeout / 5xx / 429) → lookup_failed (ADR-016).
"""

from __future__ import annotations

from research_harness.sources import existence
from research_harness.sources.transport import HttpRequest, HttpResponse


def _tx(resp: HttpResponse):
    def transport(_req: HttpRequest) -> HttpResponse:
        return resp

    return transport


def test_doi_matched() -> None:
    assert (
        existence.check_doi("10.1/x", transport=_tx(HttpResponse(status=200, body=b"{}")))
        == "matched"
    )


def test_doi_not_found() -> None:
    assert existence.check_doi("10.1/x", transport=_tx(HttpResponse(status=404))) == "not_found"


def test_doi_timeout_is_lookup_failed() -> None:
    assert (
        existence.check_doi("10.1/x", transport=_tx(HttpResponse(status=None, error="timeout")))
        == "lookup_failed"
    )


def test_doi_server_error_is_lookup_failed_not_not_found() -> None:
    # 5xx is transient; must never collapse to not_found (ADR-016 p.5).
    result = existence.check_doi("10.1/x", transport=_tx(HttpResponse(status=503)))
    assert result == "lookup_failed"


def test_url_dead_and_failed() -> None:
    assert existence.check_url("http://x", transport=_tx(HttpResponse(status=404)))[1] == "dead"
    assert (
        existence.check_url("http://x", transport=_tx(HttpResponse(status=None, error="network")))[
            1
        ]
        == "lookup_failed"
    )
