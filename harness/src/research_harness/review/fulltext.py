"""Document-wide deterministic checks (`rh review fulltext`, M3-04, FR-49).

No LLM. These run over the current unit bodies of the whole object and feed the
integration review (map.md + summaries + these results, review.md). The checks:

- ``fulltext.crossref`` (blocker) — every ``{{ref:U-...}}`` resolves to a unit.
- ``fulltext.cite_keys`` (blocker) — every cite key in the text exists in the
  bibliography (``sources/registry.jsonl``). The reverse direction (a source
  never cited) is rule-pack governed and lands with M3-23.
- ``fulltext.repeated_fragment`` (major) — a normalized word shingle of
  >= 40 words that occurs in two different units (D16).
- glossary consistency — delegated to the glossary module (``fulltext.term_glossary``
  in spec terms; the glossary check owns the finding ids).

Numbering (needs figure/table infra) and volume (needs thesis.md) are deferred.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from research_harness.sources import registry as registry_mod
from research_harness.structure import ops
from research_harness.summaries import glossary as glossary_mod
from research_harness.summaries.deterministic import body_of

_CROSSREF = re.compile(r"\{\{ref:(U-[0-9A-HJKMNP-TV-Z]{8})\}\}")
_CITE = re.compile(r"@([A-Za-z0-9:_-]+)|\[\[cite:([^\]]+)\]\]")
_WORD = re.compile(r"\w+", re.UNICODE)

SHINGLE_WORDS = 40


def _bodies(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for uid, folder in ops.current_folders(root).items():
        tf = folder / "text.md"
        if tf.is_file():
            out[uid] = body_of(tf.read_text(encoding="utf-8"))
    return out


def _f(check_id: str, severity: str, reason: str, **extra: Any) -> dict[str, Any]:
    out: dict[str, Any] = {
        "check_id": check_id,
        "severity": severity,
        "reason": reason,
        "location": extra.pop("location", {}),
        "proposed_action": extra.pop("proposed_action", ""),
    }
    out.update(extra)
    return out


def check_crossref(bodies: dict[str, str]) -> list[dict[str, Any]]:
    known = set(bodies)
    findings: list[dict[str, Any]] = []
    for uid, body in bodies.items():
        for ref in _CROSSREF.findall(body):
            if ref not in known:
                findings.append(
                    _f(
                        "fulltext.crossref",
                        "blocker",
                        f"{uid}: cross-reference {ref!r} resolves to no unit",
                        location={"ref": f"unit:{uid}"},
                        observed=ref,
                        proposed_action="Fix the reference or add the target unit.",
                    )
                )
    return findings


def _cite_keys(body: str) -> set[str]:
    return {m.group(1) or m.group(2) for m in _CITE.finditer(body)}


def check_cite_keys(bodies: dict[str, str], source_ids: set[str]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for uid, body in bodies.items():
        for key in sorted(_cite_keys(body)):
            if key not in source_ids:
                findings.append(
                    _f(
                        "fulltext.cite_keys",
                        "blocker",
                        f"{uid}: cite key {key!r} is not in the bibliography",
                        location={"ref": f"unit:{uid}"},
                        observed=key,
                        proposed_action="Add the source to the library or fix the cite key.",
                    )
                )
    return findings


def _shingles(body: str, n: int) -> set[tuple[str, ...]]:
    words = [w.lower() for w in _WORD.findall(body)]
    return (
        {tuple(words[i : i + n]) for i in range(len(words) - n + 1)} if len(words) >= n else set()
    )


def check_repeated_fragment(
    bodies: dict[str, str], *, min_words: int = SHINGLE_WORDS
) -> list[dict[str, Any]]:
    """A shingle of >= min_words appearing in two different units (D16)."""
    seen: dict[tuple[str, ...], str] = {}
    reported: set[tuple[str, ...]] = set()
    findings: list[dict[str, Any]] = []
    for uid in sorted(bodies):
        for sh in _shingles(bodies[uid], min_words):
            first = seen.get(sh)
            if first is None:
                seen[sh] = uid
            elif first != uid and sh not in reported:
                reported.add(sh)
                fragment = " ".join(sh)
                snippet = fragment[:80] + ("…" if len(fragment) > 80 else "")
                findings.append(
                    _f(
                        "fulltext.repeated_fragment",
                        "major",
                        f"{min_words}-word fragment repeated in {first} and {uid}: {snippet!r}",
                        location={"ref": f"unit:{uid}"},
                        proposed_action="Rewrite or cite one occurrence.",
                    )
                )
    return findings


def run(root: Path) -> list[dict[str, Any]]:
    bodies = _bodies(root)
    # Cite markers carry the source's bib_key (e.g. [[cite:meng2024]]), not its
    # internal id (S-0001), so the bibliography is the set of bib_keys. Matching
    # against ids falsely blocked every real citation.
    source_ids = {s["bib_key"] for s in registry_mod.load(root) if s.get("bib_key")}
    findings: list[dict[str, Any]] = []
    findings.extend(check_crossref(bodies))
    findings.extend(check_cite_keys(bodies, source_ids))
    findings.extend(check_repeated_fragment(bodies))
    findings.extend(glossary_mod.check(root))
    return findings
