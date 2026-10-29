"""Monotonic ULID generator (stdlib only).

A ULID is a 128-bit value — 48-bit millisecond timestamp + 80-bit randomness —
rendered as 26 Crockford base32 characters (02 §1.2). Monotonic within a
process: two ULIDs generated in the same millisecond keep lexicographic order
by incrementing the random component.
"""

from __future__ import annotations

import os
import threading
import time

# Crockford base32 alphabet (excludes I, L, O, U).
_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_TIME_LEN = 10
_RAND_LEN = 16
_RAND_BITS = 80
_MAX_RAND = (1 << _RAND_BITS) - 1
_MAX_TIME = (1 << 48) - 1

_lock = threading.Lock()
_last_ms = -1
_last_rand = 0


def _encode(value: int, length: int) -> str:
    chars = []
    for _ in range(length):
        value, rem = divmod(value, 32)
        chars.append(_ALPHABET[rem])
    return "".join(reversed(chars))


def _now_ms() -> int:
    return int(time.time() * 1000)


def new_ulid(now_ms: int | None = None) -> str:
    """Return a new monotonic ULID string (26 chars)."""
    global _last_ms, _last_rand
    with _lock:
        ms = _now_ms() if now_ms is None else now_ms
        if ms < 0 or ms > _MAX_TIME:
            raise ValueError(f"timestamp out of ULID range: {ms}")
        if ms == _last_ms:
            _last_rand += 1
            if _last_rand > _MAX_RAND:
                # Randomness overflow within a millisecond: wait for the next.
                while ms <= _last_ms:
                    ms = _now_ms()
                _last_rand = int.from_bytes(os.urandom(10), "big")
        else:
            _last_rand = int.from_bytes(os.urandom(10), "big")
        _last_ms = ms
        rand = _last_rand
    return _encode(ms, _TIME_LEN) + _encode(rand, _RAND_LEN)


def is_ulid(value: str) -> bool:
    """True if ``value`` is a syntactically valid ULID."""
    if len(value) != _TIME_LEN + _RAND_LEN:
        return False
    return all(ch in _ALPHABET for ch in value)
