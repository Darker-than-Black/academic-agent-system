"""Fault injection for commit-protocol tests (02 §5.3, step hooks).

Honoured only when ``RH_TEST_MODE=1``. ``RH_FAULT_AT=<step>`` raises at that
step; with ``RH_FAULT_KILL=1`` it hard-exits the process (``os._exit``) to
simulate a power loss with no cleanup.
"""

from __future__ import annotations

import os

# The nine commit steps (02 §5.3).
STEPS = (
    "recovery_lock",
    "dirty_check",
    "staging",
    "blobs",
    "snapshot",
    "materialize",
    "current",
    "event",
    "cleanup",
)


def fault_point(step: str) -> None:
    if os.environ.get("RH_TEST_MODE") != "1":
        return
    if os.environ.get("RH_FAULT_AT") != step:
        return
    if os.environ.get("RH_FAULT_KILL") == "1":
        os._exit(99)
    raise RuntimeError(f"injected fault at step {step!r}")
