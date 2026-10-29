"""Envelope builder (03 §1.1).

Every command prints exactly one envelope. The ``message`` is resolved from an
i18n key so no user-facing sentence is hard-coded (02 §1.6). Schema validation
against ``envelope.schema.json`` is wired in once M1-03 lands; the field shape
here matches 03 §1.1.
"""

from __future__ import annotations

from typing import Any

from research_harness.core.errors import RhError
from research_harness.i18n import t

SCHEMA_VERSION = "0.2"
VALID_STATUS = ("ok", "partial", "blocked", "invalid", "failed", "corrupt")


def build_envelope(
    *,
    command: str,
    status: str,
    lang: str,
    message_key: str,
    message_params: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    operation_id: str | None = None,
    object_id: str | None = None,
    artifacts: list[dict[str, Any]] | None = None,
    findings: list[dict[str, Any]] | None = None,
    next_actions: list[dict[str, Any]] | None = None,
    usage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build an envelope dict. ``message`` is resolved from ``message_key``."""
    if status not in VALID_STATUS:
        raise ValueError(f"invalid envelope status: {status!r}")
    envelope: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "command": command,
        "status": status,
        "lang": lang,
        "message": t(message_key, lang, **(message_params or {})),
    }
    if operation_id is not None:
        envelope["operation_id"] = operation_id
    if object_id is not None:
        envelope["object_id"] = object_id
    if artifacts is not None:
        envelope["artifacts"] = artifacts
    if findings is not None:
        envelope["findings"] = findings
    if next_actions is not None:
        envelope["next_actions"] = next_actions
    if usage is not None:
        envelope["usage"] = usage
    envelope["data"] = data or {}
    return envelope


def error_envelope(err: RhError, *, command: str, lang: str) -> dict[str, Any]:
    """Build an envelope for a raised :class:`RhError`."""
    return build_envelope(
        command=command,
        status=err.status,
        lang=lang,
        message_key=err.message_key,
        message_params=err.params,
    )
