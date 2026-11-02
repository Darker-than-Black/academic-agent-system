"""Style profile and the stylization invariant check (integrity.md; M3-13,
FR-19, FR-19a).

A style profile is built from the author's corpus per language. Stylization must
never change the facts: ``invariant_check`` compares numbers, citation markers
and qualifiers/limitations before and after, and blocks
(``integrity.style_invariants``) if any differ (T19, FR-19a — invariants hold
100 %). No code path here edits the author's text; profiles are data.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

_NUMBER = re.compile(r"\d+(?:[.,]\d+)?%?")
_CITES = (
    re.compile(r"\[\[cite:[^\]]+\]\]"),
    re.compile(r"(?<![\w])@[\w:-]+"),
    re.compile(r"\{\{ref:[^}]+\}\}"),
    re.compile(r"\[\d+\]"),
)
_QUALIFIERS = {
    "можливо",
    "ймовірно",
    "приблизно",
    "близько",
    "майже",
    "десь",
    "maybe",
    "approximately",
    "about",
    "likely",
    "around",
    "nearly",
    "roughly",
}
_LIMIT_MARKERS = {"обмеження", "limitation", "limitations", "caveat", "застереження"}


def _numbers(text: str) -> Counter[str]:
    return Counter(m.group(0).replace(",", ".") for m in _NUMBER.finditer(text))


def _citations(text: str) -> Counter[str]:
    c: Counter[str] = Counter()
    for pat in _CITES:
        c.update(pat.findall(text))
    return c


def _words(text: str) -> list[str]:
    return re.findall(r"[^\W_]+", text.casefold(), re.UNICODE)


def _qualifiers(text: str) -> Counter[str]:
    return Counter(w for w in _words(text) if w in _QUALIFIERS)


def _limitations(text: str) -> Counter[str]:
    return Counter(w for w in _words(text) if w in _LIMIT_MARKERS)


def invariant_check(before: str, after: str) -> list[dict[str, Any]]:
    """Block when stylization changed numbers, citations, qualifiers or
    limitation markers (FR-19a). Empty list = invariants preserved."""
    findings: list[dict[str, Any]] = []
    for name, fn in (
        ("numbers", _numbers),
        ("citations", _citations),
        ("qualifiers", _qualifiers),
        ("limitations", _limitations),
    ):
        b, a = fn(before), fn(after)
        if b != a:
            removed = list((b - a).elements())
            added = list((a - b).elements())
            findings.append(
                {
                    "check_id": "integrity.style_invariants",
                    "severity": "blocker",
                    "reason": f"{name} changed by stylization (removed={removed}, added={added})",
                    "location": {},
                    "observed": name,
                    "proposed_action": "Keep numbers, citations and qualifiers unchanged.",
                }
            )
    return findings


# --- Profile building (deterministic features) ------------------------------

_CONNECTIVES = {
    "однак",
    "проте",
    "отже",
    "тому",
    "оскільки",
    "таким",
    "крім",
    "водночас",
    "however",
    "therefore",
    "thus",
    "moreover",
    "whereas",
    "although",
    "hence",
}


def _voice_counts(text: str, markers: dict[str, dict[str, list[str]]], lang: str) -> dict[str, int]:
    low = text.casefold()
    return {
        voice: sum(low.count(m.casefold()) for m in by_lang.get(lang, []))
        for voice, by_lang in markers.items()
    }


def build_profile(
    texts: list[str],
    lang: str,
    *,
    voice_markers: dict[str, dict[str, list[str]]],
    version: int = 1,
    built_from: list[str] | None = None,
) -> dict[str, Any]:
    """Deterministic style features from the author's corpus for one language."""
    joined = "\n".join(texts)
    sentences = [s for s in re.split(r"[.!?]+", joined) if s.strip()]
    words_per = [len(_words(s)) for s in sentences] or [0]
    counts = _voice_counts(joined, voice_markers, lang)
    voice = max(counts, key=lambda k: counts[k]) if any(counts.values()) else "impersonal"
    conn = Counter(w for w in _words(joined) if w in _CONNECTIVES)
    return {
        "lang": lang,
        "version": version,
        "built_from": built_from or [],
        "features": {
            "sentence_length": round(sum(words_per) / len(words_per), 1),
            "voice": voice,
            "connectives": [w for w, _ in conn.most_common(5)],
            "preferred_terms": {},
            "banned_phrases": [],
        },
        "accepted_proposals": [],
    }
