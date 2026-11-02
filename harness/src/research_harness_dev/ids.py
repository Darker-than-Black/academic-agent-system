"""Unit / paragraph ID helper for fixtures and dev tooling (PH-1).

Hand-typed unit (``U-`` + 8) and paragraph (``PG-`` + 6) IDs repeatedly slipped
in characters outside the Crockford base32 alphabet (``I L O U`` are excluded),
shipping IDs that later failed validation. This helper is the single place dev
code builds such IDs: it validates against the core patterns at construction, so
a bad character fails loudly here instead of downstream.

Fixtures must stay reproducible (H6): they use the validating constructors
(:func:`unit_id` / :func:`paragraph_id`) with explicit suffixes, or the
deterministic :func:`mint_unit_id` / :func:`mint_paragraph_id`. Random minting
is re-exported for non-fixture callers that need collision-safe IDs.

May import ``research_harness``; never the reverse (01 §2, H5).
"""

from __future__ import annotations

from research_harness.core.ids import (
    _CROCKFORD as _ALPHABET,  # single source of truth for the alphabet
)
from research_harness.core.ids import (
    is_valid,
    new_paragraph_id,
    new_unit_id,
)

_UNIT_LEN = 8
_PARA_LEN = 6

__all__ = [
    "unit_id",
    "paragraph_id",
    "is_valid_unit_id",
    "is_valid_paragraph_id",
    "mint_unit_id",
    "mint_paragraph_id",
    "new_unit_id",
    "new_paragraph_id",
]


def is_valid_unit_id(value: str) -> bool:
    """True if ``value`` is a well-formed unit id (``U-`` + 8 Crockford chars)."""
    return is_valid("unit", value)


def is_valid_paragraph_id(value: str) -> bool:
    """True if ``value`` is a well-formed paragraph id (``PG-`` + 6 Crockford)."""
    return is_valid("paragraph", value)


def unit_id(suffix: str) -> str:
    """Build and validate ``U-<suffix>``; raise ``ValueError`` if malformed."""
    value = f"U-{suffix}"
    if not is_valid_unit_id(value):
        raise ValueError(
            f"invalid unit id suffix {suffix!r}: need {_UNIT_LEN} Crockford "
            f"base32 chars (0-9 A-Z, excluding I L O U)"
        )
    return value


def paragraph_id(suffix: str) -> str:
    """Build and validate ``PG-<suffix>``; raise ``ValueError`` if malformed."""
    value = f"PG-{suffix}"
    if not is_valid_paragraph_id(value):
        raise ValueError(
            f"invalid paragraph id suffix {suffix!r}: need {_PARA_LEN} Crockford "
            f"base32 chars (0-9 A-Z, excluding I L O U)"
        )
    return value


def _encode(index: int, width: int) -> str:
    """Zero-padded Crockford base32 of a non-negative ``index``."""
    if index < 0:
        raise ValueError("index must be non-negative")
    base = len(_ALPHABET)  # 32
    out = ""
    n = index
    while n:
        n, rem = divmod(n, base)
        out = _ALPHABET[rem] + out
    out = out or _ALPHABET[0]
    if len(out) > width:
        raise ValueError(f"index {index} does not fit in {width} Crockford chars")
    return out.rjust(width, _ALPHABET[0])


def mint_unit_id(index: int) -> str:
    """Deterministic valid unit id for a non-negative ``index`` (reproducible)."""
    return unit_id(_encode(index, _UNIT_LEN))


def mint_paragraph_id(index: int) -> str:
    """Deterministic valid paragraph id for a non-negative ``index``."""
    return paragraph_id(_encode(index, _PARA_LEN))
