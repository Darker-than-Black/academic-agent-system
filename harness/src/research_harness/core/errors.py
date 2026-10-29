"""Exception classes mapped to CLI exit codes and envelope statuses (03 §1.2).

Each error carries an i18n message *key* (never a hard-coded sentence); the
sentence is resolved when the envelope is built.
"""

from __future__ import annotations

# Exit codes (03 §1.2).
EXIT_OK = 0
EXIT_INVALID = 2
EXIT_BLOCKED = 3
EXIT_FAILED = 4
EXIT_CORRUPT = 5


class RhError(Exception):
    """Base error. Subclasses fix ``exit_code`` and ``status``."""

    exit_code: int = EXIT_FAILED
    status: str = "failed"
    default_key: str = "error.failed"

    def __init__(
        self,
        message_key: str | None = None,
        *,
        params: dict[str, object] | None = None,
    ) -> None:
        self.message_key = message_key or self.default_key
        self.params = params or {}
        super().__init__(self.message_key)


class InvalidInputError(RhError):
    exit_code = EXIT_INVALID
    status = "invalid"
    default_key = "error.invalid"


class BlockedError(RhError):
    exit_code = EXIT_BLOCKED
    status = "blocked"
    default_key = "error.blocked"


class ToolFailureError(RhError):
    exit_code = EXIT_FAILED
    status = "failed"
    default_key = "error.failed"


class CorruptStateError(RhError):
    exit_code = EXIT_CORRUPT
    status = "corrupt"
    default_key = "error.corrupt"
