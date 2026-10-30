"""HTTP transport for source adapters — stdlib only, injectable (H5, H9).

The default transport uses :mod:`urllib` (no third-party HTTP client, no LLM
SDK). Every adapter and the existence check take a ``transport`` callable so
tests run on recorded fixtures with no live calls, and no paid endpoint is ever
reached. Transient failures are surfaced as ``error`` kinds, not exceptions, so
callers can map them to ``lookup_failed`` (never ``not_found``) per ADR-016.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class HttpRequest:
    url: str
    method: str = "GET"
    headers: dict[str, str] = field(default_factory=dict)
    timeout: float = 10.0


@dataclass
class HttpResponse:
    status: int | None  # HTTP status, or None when the transport itself failed
    body: bytes = b""
    error: str | None = None  # "timeout" | "network" | None


Transport = Callable[[HttpRequest], HttpResponse]


def urllib_transport(req: HttpRequest) -> HttpResponse:
    """Default transport. Never raises for HTTP errors; maps failures to kinds."""
    request = urllib.request.Request(req.url, method=req.method, headers=req.headers)
    try:
        with urllib.request.urlopen(request, timeout=req.timeout) as resp:  # noqa: S310
            return HttpResponse(status=resp.status, body=resp.read())
    except urllib.error.HTTPError as exc:  # 4xx / 5xx are responses, not failures
        try:
            body = exc.read()
        except Exception:  # noqa: BLE001
            body = b""
        return HttpResponse(status=exc.code, body=body)
    except TimeoutError:
        return HttpResponse(status=None, error="timeout")
    except urllib.error.URLError as exc:
        err = "timeout" if isinstance(exc.reason, TimeoutError) else "network"
        return HttpResponse(status=None, error=err)
    except Exception:  # noqa: BLE001
        return HttpResponse(status=None, error="network")


def is_transient(resp: HttpResponse) -> bool:
    """True for failures that must become ``lookup_failed`` (timeout, 5xx, 429)."""
    if resp.error is not None:
        return True
    return resp.status is not None and (resp.status == 429 or resp.status >= 500)
