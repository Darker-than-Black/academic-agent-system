"""Dictation (FR-52, T57): keep the raw transcript, structure it into the unit
with the author's wording, and report the share of preserved phrases.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from research_harness.core.clock import default_clock
from research_harness.units.write import write_body

_SENT = re.compile(r"[^.!?\n]+[.!?]?")


def dictation_dir(root: Path) -> Path:
    d = root / "history" / "dictation"
    d.mkdir(parents=True, exist_ok=True)
    return d


def import_transcript(
    root: Path, unit_id: str, transcript: str, *, audio_ref: str | None = None
) -> dict[str, Any]:
    """Store the raw transcript immutably and propose a structuring."""
    ts = default_clock().now_rfc3339().replace(":", "").replace("-", "")
    raw_path = dictation_dir(root) / f"{unit_id}_{ts}.txt"
    raw_path.write_text(transcript, encoding="utf-8")
    proposal = _structure(transcript)
    return {
        "unit_id": unit_id,
        "raw_path": str(raw_path.relative_to(root)),
        "audio_ref": audio_ref,
        "proposal": proposal,
    }


def _structure(transcript: str) -> str:
    """Minimal structuring: keep wording, split into paragraphs at blank lines."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", transcript.strip()) if p.strip()]
    return "\n\n".join(paragraphs)


def accept_structuring(root: Path, unit_id: str, structured_body: str) -> list[dict[str, str]]:
    """After the author's OK: the structured paragraphs are the author's (origin author)."""
    return write_body(root, unit_id, structured_body, by="author")


def _phrases(text: str) -> list[str]:
    return [m.group(0).strip() for m in _SENT.finditer(text) if m.group(0).strip()]


def preserved_phrase_share(raw: str, structured: str) -> float:
    """Share of raw-transcript phrases that appear verbatim in the structured text."""
    raw_phrases = _phrases(raw)
    if not raw_phrases:
        return 1.0
    kept = sum(1 for p in raw_phrases if p in structured)
    return round(kept / len(raw_phrases), 3)
