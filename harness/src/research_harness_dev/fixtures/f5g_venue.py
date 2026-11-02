"""F5g — venue-status fixture (M3-22, T39, D14).

Records two synthetic venue checks (H6): one with an ``unknown`` status because
no indexing evidence was found (D14 — the value stays ``unknown``, H7, never a
guess), and one with ``not_included``. Both drive ``integrity.venue_status``
findings, so a verified export is blocked until the author resolves the venue.
"""

from __future__ import annotations

from pathlib import Path

from research_harness.integrity import venue as venue_mod


def build_f5g(dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    # D14: no evidence → unknown (the status is never fabricated, H7).
    venue_mod.record_check(
        dest,
        title="Synthetic Journal of Nothing",
        resource="scopus_sources",
        query_date="2026-05-01",
        status_value="unknown",
        status_date="2026-05-01",
        checked_by="fixture",
    )
    venue_mod.record_check(
        dest,
        title="Predatory Quarterly (synthetic)",
        resource="doaj",
        query_date="2026-05-01",
        status_value="not_included",
        status_date="2026-05-01",
        checked_by="fixture",
    )
    return dest
