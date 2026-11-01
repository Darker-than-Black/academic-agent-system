"""Finding index and human-only resolution (review.md; M3-05, FR-23/FR-35).

The index (`findings/index.jsonl`) holds the current status of every finding
raised by a review, and its append-only resolution history. Accept / reject is
human-only — the same channel rule as gates (02 §9.3): an agent call produces a
resolution *request*, never a decision (H14).
"""

from __future__ import annotations

from research_harness.findings.index import (
    STATUSES,
    add,
    index_path,
    list_findings,
    load,
    resolve,
)

__all__ = ["STATUSES", "add", "index_path", "list_findings", "load", "resolve"]
