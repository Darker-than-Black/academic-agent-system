"""Numbers-from-sources check (M3-03, ADR-009 p.4).

Deterministic aid for the unit / chapter critic: every number stated in a claim
that cites an external source must appear in one of that claim's cited excerpts.
A number present in the claim but in none of its excerpts is flagged
``review.number_not_in_excerpt`` (major) — the pointer a critic needs to catch a
percentage reported as percentage points (D7) or a figure lifted from a
different table or group (D8). Numbers are compared as normalized tokens, never
as substrings, so ``7`` never matches ``17`` and ``42`` never matches ``42%``.

This never checks every number in the document against every source: it only
compares a claim's own numbers to that claim's own cited excerpts (ADR-009 p.4).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from research_harness.claims import ledger as ledger_mod
from research_harness.evidence import excerpts as excerpts_mod

_NUM_RE = re.compile(r"\d+(?:[.,]\d+)?\s*%?")
_EXTERNAL = ("external",)


def extract_numbers(text: str) -> set[str]:
    """Normalized numeric tokens in ``text`` (decimal comma -> dot, spaces gone,
    a trailing ``%`` kept so a percentage differs from a bare count)."""
    out: set[str] = set()
    for m in _NUM_RE.findall(text or ""):
        tok = m.replace(" ", "").replace(" ", "").replace(",", ".")
        if tok:
            out.add(tok)
    return out


def _cited_excerpt_numbers(claim: dict[str, Any], by_id: dict[str, dict[str, Any]]) -> set[str]:
    nums: set[str] = set()
    for ev in claim.get("evidence", []):
        if ev.get("type") == "excerpt":
            exc = by_id.get(ev.get("id"))
            if exc:
                nums |= extract_numbers(exc.get("text", ""))
    return nums


def check_claim_numbers(
    claim: dict[str, Any], by_id: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """Findings for numbers in ``claim`` absent from its cited excerpts."""
    if claim.get("kind") not in _EXTERNAL:
        return []
    cited = [ev for ev in claim.get("evidence", []) if ev.get("type") == "excerpt"]
    if not cited:
        return []  # no excerpt to check against; coverage handles missing evidence
    claim_nums = extract_numbers(claim.get("text", ""))
    if not claim_nums:
        return []
    present = _cited_excerpt_numbers(claim, by_id)
    missing = sorted(claim_nums - present)
    findings: list[dict[str, Any]] = []
    for num in missing:
        findings.append(
            {
                "check_id": "review.number_not_in_excerpt",
                "severity": "major",
                "reason": (
                    f"{claim['id']}: number {num!r} is not in any cited excerpt"
                    " (check for a percent/percentage-point or wrong-table mismatch)"
                ),
                "location": {"ref": f"claim:{claim['id']}"},
                "observed": num,
                "proposed_action": "Verify the number against the source excerpt and locator.",
            }
        )
    return findings


def check_unit_numbers(root: Path, unit_id: str) -> list[dict[str, Any]]:
    """Run the numbers check over every external claim of a unit."""
    by_id = {e["id"]: e for e in excerpts_mod.load_excerpts(root)}
    findings: list[dict[str, Any]] = []
    for claim in ledger_mod.load_unit_claims(root, unit_id):
        findings.extend(check_claim_numbers(claim, by_id))
    return findings
