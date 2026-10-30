"""Adapter base: request budget, HTTP status mapping, result envelope.

Every call goes through :meth:`BaseAdapter.fetch_json`, which counts the request
(``RequestBudget``; money stays ``unknown``, paid disabled — H9), performs the
GET through the injected transport, retries transient failures ≤ 2 times, and
maps the outcome to a module-contract status (04-modules/sources-library.md):
``ok | unavailable | blocked | budget_exhausted | lookup_failed | not_found``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from research_harness.core.clock import default_clock
from research_harness.sources.transport import (
    HttpRequest,
    HttpResponse,
    Transport,
    is_transient,
    urllib_transport,
)

_MAX_ATTEMPTS = 3  # 1 try + 2 retries (card M2-01 step 2)


class RequestBudget:
    """Counts requests. Never blocks (open APIs only); money stays ``unknown``.

    The full cost guard (ADR-017 thresholds, ARC #22) lands in M2-09 and will
    wrap this; here we only count so every call is accountable (NFR-05).
    """

    UNKNOWN = "unknown"

    def __init__(self) -> None:
        self.requests = 0

    def check(self, resource: str) -> bool:  # noqa: ARG002 - resource kept for M2-09
        self.requests += 1
        return True

    @property
    def money(self) -> str:
        return self.UNKNOWN


@dataclass
class AdapterResult:
    resource: str
    status: str
    retrieved_at: str
    request: dict[str, Any]
    records: list[dict[str, Any]] = field(default_factory=list)
    http_status: int | None = None

    @property
    def ok(self) -> bool:
        return self.status == "ok"


def _params_hash(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


def _status_for(resp: HttpResponse) -> str:
    if resp.error is not None:  # timeout / network after retries
        return "lookup_failed"
    code = resp.status
    if code == 200:
        return "ok"
    if code == 404:
        return "not_found"
    if code in (401, 403):
        return "blocked"
    if code == 429:
        return "budget_exhausted"
    if code is not None and code >= 500:
        return "unavailable"
    return "lookup_failed"


class BaseAdapter:
    resource_name: str = "base"

    def __init__(
        self,
        *,
        transport: Transport | None = None,
        budget: RequestBudget | None = None,
    ) -> None:
        self.transport = transport or urllib_transport
        self.budget = budget or RequestBudget()

    # --- HTTP -----------------------------------------------------------
    def _headers(self) -> dict[str, str]:
        return {
            "User-Agent": "research-harness/0.1 "
            "(https://github.com/Darker-than-Black/academic-agent-system)",
            "Accept": "application/json",
        }

    def fetch(self, url: str, *, headers: dict[str, str] | None = None) -> HttpResponse:
        """GET ``url`` through the transport with retries for transient failures."""
        self.budget.check(self.resource_name)
        hdrs = {**self._headers(), **(headers or {})}
        resp: HttpResponse | None = None
        for _ in range(_MAX_ATTEMPTS):
            resp = self.transport(HttpRequest(url=url, headers=hdrs))
            if not is_transient(resp):
                break
        assert resp is not None
        return resp

    def fetch_json(
        self, url: str, *, headers: dict[str, str] | None = None
    ) -> tuple[str, int | None, Any]:
        """Return ``(status, http_status, parsed_json_or_None)``."""
        resp = self.fetch(url, headers=headers)
        status = _status_for(resp)
        data: Any = None
        if status == "ok":
            try:
                data = json.loads(resp.body.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                status = "lookup_failed"
        return status, resp.status, data

    def result(
        self, *, status: str, url: str, http_status: int | None, records: list[dict[str, Any]]
    ) -> AdapterResult:
        return AdapterResult(
            resource=self.resource_name,
            status=status,
            retrieved_at=default_clock().now_rfc3339(),
            request={"endpoint": url, "params_hash": _params_hash(url)},
            records=records,
            http_status=http_status,
        )

    # --- Subclass contract ---------------------------------------------
    def lookup_by_doi(self, doi: str) -> AdapterResult:  # pragma: no cover - abstract
        raise NotImplementedError

    def normalize(self, raw: Any) -> dict[str, Any]:  # pragma: no cover - abstract
        raise NotImplementedError
