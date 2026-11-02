"""Analysis sandbox (M3-18+, analysis-sandbox.md).

Reproducible local analysis of open data and public documents: a dataset
registry that admits nothing without recorded terms (FR-57), a per-object ``uv``
project, and a network-off execution sandbox (FR-39, NFR-08). Core is LLM-free
(H5); no paid or remote compute (H9) — analysis runs locally with the network
disabled. Nothing simulated is ever presented as real (FR-59).

M3-18 provides the registry and the sandbox scaffolding; runs, result rows and
figures build on it (M3-19/M3-20/M3-21).
"""

from __future__ import annotations
