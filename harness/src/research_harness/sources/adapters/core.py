"""CORE adapter — DEFERRED (docs could not be verified).

Every CORE docs endpoint (``api.core.ac.uk/docs/v3``, ``/v3/openapi.json``,
``core.ac.uk/documentation/api``, ``core.ac.uk/services/api``) returned HTTP 403
to automated fetches on 2026-10-30, so the base URL, the ``Authorization:
Bearer`` header and the work-response schema could NOT be confirmed against
official docs. H12 forbids guessing API syntax from memory or the spec, so this
adapter makes NO calls and reports the resource as ``unavailable`` with the
reason ``docs_unverified`` (surfaced as a coverage gap, FR-20) until the docs
are verified (then the normalize/lookup logic is filled in and the policy
``docs_unverified`` flag and ``base_url: unknown`` are replaced).
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
