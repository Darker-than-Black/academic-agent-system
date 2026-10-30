"""Review v0 (M2-11): data side of the unit critic and the article integration
review — validate and store reviewer handoffs, cap verdicts, compute coverage.
The full multilevel review and its semantic eval thresholds are M3.

A reviewer runs in a fresh context with its pack (no writing history, FR-14).
No check ever reports "PASS": coverage is checked/denominator with the unchecked
claims listed.
"""

from __future__ import annotations
