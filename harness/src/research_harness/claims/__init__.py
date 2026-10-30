"""Claim ledger, deterministic support caps, and claim extraction (M2-06).

Every material statement in a unit is a claim with typed evidence. Caps are
deterministic and applied before any semantic verdict: no cap ever raises
support, and topic-match without an explicit, quote-checked statement is never
``supported`` (claims-text.md, N1; ADR-013).
"""

from __future__ import annotations

PRODUCER = {"kind": "tool", "name": "rh", "version": "0.2"}
