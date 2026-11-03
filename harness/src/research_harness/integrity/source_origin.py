"""Source language / jurisdiction check (integrity.md; M4-13, FR-27, FR-37).

Ukrainian cat. «Б» guidance: do not cite or include in the bibliography sources
published in Russian in any country, nor sources published on the territory of
russia or belarus. This module reports such sources from the corpus; it never
removes a source (that is the author's edit, H13) and never guesses an origin —
a missing language/country stays ``unknown`` (H7) and is surfaced for the author
to resolve.

Severities follow the ua-fahove-b ``sources.yaml`` rule pack:
- language is Russian (any country) -> ``integrity.source_language_forbidden`` (blocker)
- publication country RU or BY -> ``integrity.source_jurisdiction_forbidden`` (blocker)
- language unknown (cannot confirm not-ru) -> ``integrity.source_origin_unknown`` (major)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from research_harness.sources import registry

# Normalized tokens that mean "Russian language".
_RU_LANG = {"ru", "rus", "russian", "русский", "російська", "ru-ru"}
# Normalized tokens for forbidden publication jurisdictions (russia, belarus).
_FORBIDDEN_COUNTRY = {
    "ru",
    "rus",
    "russia",
    "russian federation",
    "росія",
    "россия",
    "by",
    "blr",
    "belarus",
    "білорусь",
    "беларусь",
}


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _is_unknown(source: dict[str, Any]) -> bool:
    lang = _norm(source.get("language"))
    return lang in ("", "unknown")


def origin_findings(root: Path) -> list[dict[str, Any]]:
    """Report forbidden or unresolved-origin sources across the corpus."""
    findings: list[dict[str, Any]] = []
    for source in registry.load(root):
        sid = source.get("id", "?")
        lang = _norm(source.get("language"))
        country = _norm(source.get("publication_country"))

        if lang in _RU_LANG:
            findings.append(
                _f(
                    "integrity.source_language_forbidden",
                    "blocker",
                    sid,
                    f"source {sid} is published in Russian ({source.get('language')!r}); "
                    "cat. «Б» guidance forbids citing Russian-language sources",
                    observed=source.get("language"),
                    action="Remove/replace this source, or fix its language if misdetected.",
                )
            )
            continue
        if country in _FORBIDDEN_COUNTRY:
            findings.append(
                _f(
                    "integrity.source_jurisdiction_forbidden",
                    "blocker",
                    sid,
                    f"source {sid} is published in a forbidden jurisdiction "
                    f"({source.get('publication_country')!r}: russia/belarus)",
                    observed=source.get("publication_country"),
                    action="Remove/replace this source, or fix its country if misattributed.",
                )
            )
            continue
        if _is_unknown(source):
            findings.append(
                _f(
                    "integrity.source_origin_unknown",
                    "major",
                    sid,
                    f"source {sid} has no resolved language; origin cannot be confirmed "
                    "as permitted (H7)",
                    observed="unknown",
                    action="Resolve the source metadata (language, publication country) via "
                    "`rh source lookup`, or drop it.",
                )
            )
    return findings


def _f(
    check_id: str,
    severity: str,
    source_id: str,
    reason: str,
    *,
    observed: Any,
    action: str,
) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "severity": severity,
        "reason": reason,
        "location": {"ref": f"source:{source_id}"},
        "observed": observed,
        "proposed_action": action,
    }
