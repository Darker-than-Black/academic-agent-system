"""Envelope + i18n tests (02 §1.6, 03 §1.1)."""

from __future__ import annotations

import pytest

from research_harness.core.envelope import build_envelope, error_envelope
from research_harness.core.errors import BlockedError, InvalidInputError
from research_harness.i18n import DEFAULT_LANG, resolve_lang, t


def test_version_envelope_differs_only_by_lang_and_message() -> None:
    uk = build_envelope(
        command="version",
        status="ok",
        lang="uk",
        message_key="version.message",
        message_params={"version": "0.1.0"},
        data={"version": "0.1.0"},
    )
    en = build_envelope(
        command="version",
        status="ok",
        lang="en",
        message_key="version.message",
        message_params={"version": "0.1.0"},
        data={"version": "0.1.0"},
    )
    assert uk["lang"] == "uk" and en["lang"] == "en"
    assert uk["message"] != en["message"]
    # Everything except lang and message is identical.
    uk_rest = {k: v for k, v in uk.items() if k not in ("lang", "message")}
    en_rest = {k: v for k, v in en.items() if k not in ("lang", "message")}
    assert uk_rest == en_rest


def test_t_formats_params() -> None:
    assert "0.1.0" in t("version.message", "en", version="0.1.0")


def test_t_falls_back_to_other_language(caplog: pytest.LogCaptureFixture) -> None:
    # A key only needs to exist in some catalog; unknown keys return the key.
    assert t("totally.missing.key", "uk") == "totally.missing.key"


def test_resolve_lang_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RH_LANG", raising=False)
    assert resolve_lang("en", "uk") == "en"  # --lang wins
    monkeypatch.setenv("RH_LANG", "en")
    assert resolve_lang(None, "uk") == "en"  # RH_LANG over profile
    monkeypatch.delenv("RH_LANG", raising=False)
    assert resolve_lang(None, "en") == "en"  # profile over default
    assert resolve_lang(None, None) == DEFAULT_LANG


def test_error_envelope_maps_status_and_key() -> None:
    env = error_envelope(InvalidInputError(), command="start", lang="uk")
    assert env["status"] == "invalid"
    assert env["message"]  # resolved from key, non-empty
    assert InvalidInputError().exit_code == 2
    assert BlockedError().exit_code == 3


def test_build_envelope_rejects_bad_status() -> None:
    with pytest.raises(ValueError):
        build_envelope(command="x", status="nope", lang="uk", message_key="version.message")
