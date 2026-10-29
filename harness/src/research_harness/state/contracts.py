"""Stage contracts (02 §5.7).

Adapted from AutoResearchClaw (MIT)
  @ be4ba4755bf1b52220f25e13b2293b5956590070 : researchclaw/pipeline/contracts.py
Changes: kept the frozen-dataclass shape (inputs, outputs, DoD, error code,
retries); renamed input_files/output_files to inputs/outputs carrying artifact
refs instead of file names; dod is a list of deterministic check IDs rather than
a prose sentence; added a `gate` field; dropped the 23 hard-coded ResearchClaw
CONTRACTS (our stages A0–A16 / T0–T10 are data, loaded in M1-11). See adoption
record ADP-002 in harness/third_party/manifest.json.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class StageContract:
    """Declarative contract for one lifecycle stage."""

    stage: str
    inputs: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()
    dod: tuple[str, ...] = ()
    gate: str | None = None
    error_codes: tuple[str, ...] = ()
    max_retries: int = 1
    conditions: dict[str, str] = field(default_factory=dict)
