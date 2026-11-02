"""Sandbox execution capability (M3-18, FR-39/NFR-08). This module decides *how*
the network can be turned off for an analysis run and provides the pieces a run
uses; executing scripts is M3-19.

Network off during analysis (invariant 2): a Linux network namespace
(``unshare -n``) when available — recorded ``network: disabled``; otherwise a
Python-level guard injected as ``sitecustomize`` that refuses every socket —
recorded ``network: guard_only``. There is never a pretend sandbox: if a run
cannot be isolated at all the capability is ``unavailable`` and no run proceeds.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

# Injected as sitecustomize.py on PYTHONPATH for a guard_only run: it replaces
# socket connection with a hard failure, so any network attempt fails the run
# (analysis.network_attempt) instead of reaching out. Loopback is left alone so
# local multiprocessing still works.
GUARD_SITECUSTOMIZE = '''"""rh sandbox network guard (generated). Blocks outbound sockets."""
import socket as _socket

_ALLOWED = {"127.0.0.1", "::1", "localhost"}
_real_connect = _socket.socket.connect


def _guarded_connect(self, address):
    host = address[0] if isinstance(address, tuple) else None
    if host in _ALLOWED:
        return _real_connect(self, address)
    raise OSError("rh sandbox: network disabled during analysis (FR-39)")


_socket.socket.connect = _guarded_connect
_socket.socket.connect_ex = lambda self, address: 1
'''


@dataclass
class SandboxCaps:
    network: str  # "disabled" (namespace) | "guard_only" | "unavailable"
    namespace: bool


def _namespace_available() -> bool:
    """True when ``unshare -n`` can create a network namespace (Linux only)."""
    try:
        result = subprocess.run(  # noqa: S603
            ["unshare", "-n", "true"],  # noqa: S607
            capture_output=True,
            timeout=5,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def capabilities() -> SandboxCaps:
    if _namespace_available():
        return SandboxCaps(network="disabled", namespace=True)
    # The Python guard is always available, so the capability is never a pretend
    # sandbox; "unavailable" is reserved for an environment that forbids even this.
    return SandboxCaps(network="guard_only", namespace=False)


def write_guard(dir_: Path) -> Path:
    """Write the sitecustomize guard into ``dir_`` and return its path."""
    dir_.mkdir(parents=True, exist_ok=True)
    path = dir_ / "sitecustomize.py"
    path.write_text(GUARD_SITECUSTOMIZE, encoding="utf-8")
    return path


# Defaults; a run may override from config (M3-19).
DEFAULT_TIMEOUT_S = 300
DEFAULT_MEMORY_MB = 2048
