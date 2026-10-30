"""Model tiers, resolution, downgrade and call log (T63 config part)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from research_harness.core.errors import InvalidInputError
from research_harness.models import calls, config


def test_researcher_resolves_on_claude_code() -> None:
    tier, model = config.resolve("researcher", "claude-code")
    assert tier == "flagship" and model == "claude-fable-5-1"


def test_codex_flagship_is_unknown() -> None:
    tier, model = config.resolve("researcher", "codex")
    assert tier == "flagship" and model is None  # maps to unknown → no silent downgrade


def test_unknown_role_rejected() -> None:
    with pytest.raises(InvalidInputError):
        config.resolve("nope", "claude-code")


def test_downgrade_is_consumed_by_next_log(tmp_path: Path) -> None:
    calls.record_downgrade(
        tmp_path, "researcher", from_tier="flagship", to_tier="strong", reason="budget"
    )
    rec = calls.log_call(
        tmp_path,
        host="claude-code",
        role="researcher",
        tier_required="flagship",
        model_id="claude-opus-5-5",
    )
    assert rec["downgrade"] == {"from_tier": "flagship", "to_tier": "strong", "reason": "budget"}
    # Consumed once: the following call has no downgrade.
    rec2 = calls.log_call(
        tmp_path,
        host="claude-code",
        role="researcher",
        tier_required="flagship",
        model_id="claude-opus-5-5",
    )
    assert "downgrade" not in rec2


def test_missing_token_counts_stored_as_unknown_not_zero(tmp_path: Path) -> None:
    rec = calls.log_call(
        tmp_path,
        host="claude-code",
        role="writer",
        tier_required="strong",
        model_id="claude-opus-5-5",
    )
    assert (
        rec["tokens_in"] == "unknown"
        and rec["tokens_out"] == "unknown"
        and rec["cost"] == "unknown"
    )
    assert rec["tokens_in"] != 0
    lines = calls.calls_path(tmp_path).read_text(encoding="utf-8").splitlines()
    assert json.loads(lines[0])["tokens_in"] == "unknown"


def test_call_record_validates_against_schema(tmp_path: Path) -> None:
    from research_harness.schemas import validate

    rec = calls.log_call(
        tmp_path,
        host="claude-code",
        role="writer",
        tier_required="strong",
        model_id="claude-opus-5-5",
        tokens_in=10,
        tokens_out=20,
        cost=0.01,
    )
    rec["duration_s"] = "unknown"
    assert validate("model-call", rec) == []
