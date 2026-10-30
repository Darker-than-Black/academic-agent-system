"""Metadata adapters (M2-01). Each reads the resource's official docs (URL+date
recorded in its docstring, H12) and performs HTTP through an injected transport,
so CI runs on recorded fixtures with no live calls and no paid endpoint (H9)."""

from __future__ import annotations

from research_harness.sources.adapters.base import AdapterResult, BaseAdapter, RequestBudget


def get_adapter(resource: str, **kwargs: object) -> BaseAdapter:
    """Return an adapter instance for a resource name."""
    from research_harness.sources.adapters import (
        arxiv,
        core,
        crossref,
        doaj,
        eric,
        openalex,
        semantic_scholar,
        unpaywall,
    )

    registry = {
        "openalex": openalex.OpenAlexAdapter,
        "crossref": crossref.CrossrefAdapter,
        "semantic_scholar": semantic_scholar.SemanticScholarAdapter,
        "eric": eric.EricAdapter,
        "unpaywall": unpaywall.UnpaywallAdapter,
        "core": core.CoreAdapter,
        "doaj": doaj.DoajAdapter,
        "arxiv": arxiv.ArxivAdapter,
    }
    cls = registry.get(resource)
    if cls is None:
        raise KeyError(resource)
    return cls(**kwargs)  # type: ignore[arg-type]


__all__ = ["AdapterResult", "BaseAdapter", "RequestBudget", "get_adapter"]
