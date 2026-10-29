"""Identifier allocators and validators for every format in 02 §1.2.

Counter-based IDs (``M-NNNN``, ``A-YYYY-NNN`` …) are *formatted* here; the
stateful per-object/per-year counters that feed them live in `object.json` /
`.rh-workspace.json` and are incremented inside committed operations (M1-06).
Random IDs (unit, paragraph) and ULID-based IDs are *generated* here.
"""

from __future__ import annotations

import os
import re

from research_harness.core.ulid import new_ulid

# Crockford base32, excluding I, L, O, U.
_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_C = r"[0-9A-HJKMNP-TV-Z]"

# Validation patterns per entity (02 §1.2).
PATTERNS: dict[str, re.Pattern[str]] = {
    "workspace": re.compile(rf"^W-{_C}{{26}}$"),
    "article": re.compile(r"^A-\d{4}-\d{3,}$"),
    "thesis": re.compile(r"^T-\d{4}-\d{3,}$"),
    "unit": re.compile(rf"^U-{_C}{{8}}$"),
    "material": re.compile(r"^M-\d{4,}$"),
    "source": re.compile(r"^S-\d{4,}$"),
    "excerpt": re.compile(r"^E-\d{5,}$"),
    "claim": re.compile(r"^C-\d+$"),  # v0.1 pattern ^C-[0-9]+$ stays valid
    "premise": re.compile(r"^P-\d{4,}$"),
    "definition": re.compile(r"^DEF-\d{3,}$"),
    "finding": re.compile(r"^F-\d{5,}$"),
    "approval_request": re.compile(r"^AR-\d{4,}$"),
    "approval": re.compile(r"^AP-\d{4,}$"),
    "dataset": re.compile(r"^D-\d{3,}$"),
    "run": re.compile(r"^R-\d{4,}$"),
    "result_row": re.compile(r"^RR-\d{4,}-\d{4,}$"),
    "paragraph": re.compile(rf"^PG-{_C}{{6}}$"),
    "submission": re.compile(r"^SUB-\d{2,}$"),
    "publication": re.compile(r"^PUB-\d{2,}$"),
    "reviewer_comment": re.compile(r"^RC-\d{2,}$"),
    "asset": re.compile(r"^AS-\d{3,}$"),
    "thesis_task": re.compile(r"^TK-\d+$"),
    "novelty": re.compile(r"^NV-\d+$"),
    "handoff": re.compile(rf"^H-{_C}{{26}}$"),
    "operation": re.compile(rf"^op-{_C}{{26}}$"),
    "snapshot": re.compile(rf"^snap-{_C}{{26}}$"),
    "event": re.compile(rf"^ev-{_C}{{26}}$"),
    "model_call": re.compile(rf"^mc-{_C}{{26}}$"),
    "rule": re.compile(r"^[A-Z0-9][A-Z0-9-]*$"),
}

# Minimum zero-pad widths for counter IDs; they widen automatically past it.
_COUNTER_WIDTH: dict[str, int] = {
    "material": 4,
    "source": 4,
    "excerpt": 5,
    "claim": 4,
    "premise": 4,
    "definition": 3,
    "finding": 5,
    "approval_request": 4,
    "approval": 4,
    "dataset": 3,
    "run": 4,
    "submission": 2,
    "publication": 2,
    "reviewer_comment": 2,
    "asset": 3,
    "thesis_task": 1,
    "novelty": 1,
}
_COUNTER_PREFIX: dict[str, str] = {
    "material": "M-",
    "source": "S-",
    "excerpt": "E-",
    "claim": "C-",
    "premise": "P-",
    "definition": "DEF-",
    "finding": "F-",
    "approval_request": "AR-",
    "approval": "AP-",
    "dataset": "D-",
    "run": "R-",
    "submission": "SUB-",
    "publication": "PUB-",
    "reviewer_comment": "RC-",
    "asset": "AS-",
    "thesis_task": "TK-",
    "novelty": "NV-",
}


def is_valid(entity: str, value: str) -> bool:
    """True if ``value`` matches the ID pattern for ``entity``."""
    pattern = PATTERNS.get(entity)
    if pattern is None:
        raise KeyError(f"unknown entity kind: {entity}")
    return bool(pattern.match(value))


def validate(entity: str, value: str) -> str:
    """Return ``value`` if valid for ``entity``; raise ``ValueError`` otherwise."""
    if not is_valid(entity, value):
        raise ValueError(f"invalid {entity} id: {value!r}")
    return value


def _crockford(n: int) -> str:
    return "".join(_CROCKFORD[b % 32] for b in os.urandom(n))


def new_unit_id(existing: set[str] | None = None, *, max_tries: int = 1000) -> str:
    """Random ``U-`` + 8 Crockford chars, retried on collision with ``existing``."""
    existing = existing or set()
    for _ in range(max_tries):
        candidate = "U-" + _crockford(8)
        if candidate not in existing:
            return candidate
    raise RuntimeError("could not allocate a unique unit id")


def new_paragraph_id(existing: set[str] | None = None, *, max_tries: int = 1000) -> str:
    """Random ``PG-`` + 6 Crockford chars, retried on collision (M2)."""
    existing = existing or set()
    for _ in range(max_tries):
        candidate = "PG-" + _crockford(6)
        if candidate not in existing:
            return candidate
    raise RuntimeError("could not allocate a unique paragraph id")


def object_id(kind: str, year: int, n: int) -> str:
    """Format an article/thesis id: ``A-YYYY-NNN`` / ``T-YYYY-NNN``.

    ``NNN`` is zero-padded to 3 digits and widens past 999 (02 §1.2).
    """
    if kind not in ("article", "thesis"):
        raise ValueError(f"object kind must be article or thesis, got {kind!r}")
    if n < 1:
        raise ValueError("object counter starts at 1")
    prefix = "A" if kind == "article" else "T"
    return f"{prefix}-{year:04d}-{n:03d}"


def counter_id(entity: str, n: int) -> str:
    """Format a per-object counter id (``M-NNNN``, ``E-NNNNN`` …)."""
    prefix = _COUNTER_PREFIX.get(entity)
    if prefix is None:
        raise KeyError(f"{entity} is not a counter-based id")
    if n < 1:
        raise ValueError(f"{entity} counter starts at 1")
    width = _COUNTER_WIDTH[entity]
    return f"{prefix}{n:0{width}d}"


def result_row_id(run: int, row: int) -> str:
    """Format a result-row id ``RR-NNNN-NNNN`` (run + row)."""
    if run < 1 or row < 1:
        raise ValueError("run and row counters start at 1")
    return f"RR-{run:04d}-{row:04d}"


def new_workspace_id() -> str:
    return "W-" + new_ulid()


def new_operation_id() -> str:
    return "op-" + new_ulid()


def new_snapshot_id() -> str:
    return "snap-" + new_ulid()


def new_event_id() -> str:
    return "ev-" + new_ulid()


def new_model_call_id() -> str:
    return "mc-" + new_ulid()


def new_handoff_id() -> str:
    return "H-" + new_ulid()
