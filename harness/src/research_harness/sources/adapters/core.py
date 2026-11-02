"""CORE adapter — DEFERRED (docs could not be verified).

Every CORE docs endpoint (``api.core.ac.uk/docs/v3``, ``/v3/openapi.json``,
``core.ac.uk/documentation/api``, ``core.ac.uk/services/api``) returned HTTP 403
to automated fetches on 2026-10-30 and again on 2026-11-02 (P2-3 re-check), so
the base URL, the ``Authorization: Bearer`` header and the work-response schema
could NOT be confirmed against official docs — only against conflicting
third-party pages (Bearer vs ``X-API-Key``; DOI-lookup syntax unconfirmed). H12
forbids guessing API syntax from memory, the spec or third parties, and H6
forbids inventing it, so this adapter makes NO calls and reports the resource as
``unavailable`` with the reason ``docs_unverified`` (surfaced as a coverage gap,
FR-20). It is excluded from enrichment and from ``policy.available_adapters``, so
it cannot be selected for a lookup. When the official docs become fetchable, fill
in normalize/lookup and clear the policy ``docs_unverified`` flag and
``base_url: unknown``.
"""

from __future__ import annotations

from typing import Any

from research_harness.sources.adapters.base import AdapterResult, BaseAdapter


class CoreAdapter(BaseAdapter):
    resource_name = "core"

    def lookup_by_doi(self, doi: str) -> AdapterResult:  # noqa: ARG002
        return self.result(
            status="unavailable",
            url="core:docs_unverified",
            http_status=None,
            records=[],
        )

    def normalize(self, raw: Any) -> dict[str, Any]:  # pragma: no cover - deferred
        raise NotImplementedError("CORE adapter deferred: docs unverified (H12)")
