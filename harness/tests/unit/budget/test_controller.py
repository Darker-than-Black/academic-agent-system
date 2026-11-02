"""Budget controller: usage aggregation, thresholds, unknown, paid gate (M3-01)."""

from __future__ import annotations

from pathlib import Path

from research_harness.budget import controller as c
from research_harness.models import calls


def _log(root: Path, **kw: object) -> None:
    calls.log_call(
        root, host="claude-code", role="researcher", tier_required="flagship", model_id="m", **kw
    )  # type: ignore[arg-type]


def test_usage_counts_calls_and_sums_known(tmp_path: Path) -> None:
    _log(tmp_path, tokens_in=100, tokens_out=50, cost=0.2, duration_s=3.0)
    _log(tmp_path, tokens_in=10, tokens_out=5, cost=0.1, duration_s=1.0)
    u = c.usage_from_calls(tmp_path)
    assert u["model_calls"] == 2
    assert u["tokens"] == 165
    assert abs(float(u["cost"]) - 0.3) < 1e-9
    assert u["wall_time_s"] == 4.0


def test_unknown_token_propagates(tmp_path: Path) -> None:
    _log(tmp_path, tokens_in=100, tokens_out=50)  # cost/duration default to "unknown"
    _log(tmp_path)  # all unknown
    u = c.usage_from_calls(tmp_path)
    assert u["model_calls"] == 2
    assert u["tokens"] == c.UNKNOWN  # second record's unknown poisons the total
    assert u["cost"] == c.UNKNOWN


def test_external_requests_unknown_without_log(tmp_path: Path) -> None:
    assert c.usage_from_calls(tmp_path)["external_requests"] == c.UNKNOWN


def test_external_requests_counted_when_logged(tmp_path: Path) -> None:
    (tmp_path / ".rh").mkdir(exist_ok=True)
    (tmp_path / ".rh" / "external-requests.jsonl").write_text("{}\n{}\n", encoding="utf-8")
    assert c.usage_from_calls(tmp_path)["external_requests"] == 2


def test_threshold_findings() -> None:
    budget = {"scope": "object", "paid_calls": "disabled", "limits": {"tokens": 100}}
    ev = c.evaluate(budget, {"tokens": 55})
    assert ev["state"] == "ok"  # threshold crossings are info, not a state change
    assert ev["limits"]["tokens"]["state"] == "at_50pct"
    assert [f["check_id"] for f in ev["findings"]] == ["budget.threshold_50"]
    ev80 = c.evaluate(budget, {"tokens": 85})
    assert ev80["findings"][0]["check_id"] == "budget.threshold_80"
    assert ev80["limits"]["tokens"]["state"] == "at_80pct"


def test_exhausted_is_blocker() -> None:
    budget = {"scope": "object", "paid_calls": "disabled", "limits": {"tokens": 100}}
    ev = c.evaluate(budget, {"tokens": 100})
    assert ev["state"] == "exhausted"
    f = ev["findings"][0]
    assert f["check_id"] == "budget.exhausted" and f["severity"] == "blocker"


def test_unknown_usage_is_major_not_ok() -> None:
    budget = {"scope": "object", "paid_calls": "disabled", "limits": {"tokens": 100}}
    ev = c.evaluate(budget, {"tokens": c.UNKNOWN})
    assert ev["state"] == c.UNKNOWN  # never "ok"
    assert ev["findings"][0]["check_id"] == "budget.unknown_usage"
    assert ev["findings"][0]["severity"] == "major"


def test_exhausted_outranks_unknown() -> None:
    budget = {"scope": "object", "paid_calls": "disabled", "limits": {"tokens": 10, "cost": 5}}
    ev = c.evaluate(budget, {"tokens": 20, "cost": c.UNKNOWN})
    assert ev["state"] == "exhausted"


def test_check_blocks_when_exhausted() -> None:
    budget = {"scope": "object", "paid_calls": "disabled", "limits": {"model_calls": 1}}
    r = c.check(budget, {"model_calls": 1})
    assert r["allowed"] is False


def test_paid_blocked_by_default() -> None:
    r = c.check(None, {"model_calls": 0}, paid=True)
    assert r["allowed"] is False
    assert any(f["check_id"] == "budget.paid_call_disabled" for f in r["findings"])


def test_paid_allowed_with_approval() -> None:
    budget = {"scope": "object", "paid_calls": "enabled", "enabled_by": "AR-0007"}
    r = c.check(budget, {"model_calls": 0}, paid=True)
    assert r["allowed"] is True


def test_paid_enabled_without_approval_still_blocks() -> None:
    budget = {"scope": "object", "paid_calls": "enabled"}  # no enabled_by
    r = c.check(budget, {"model_calls": 0}, paid=True)
    assert r["allowed"] is False


def test_unknown_tokens_path_relies_on_calls_and_wall(tmp_path: Path) -> None:
    """P1-3: when a host (Claude Code) cannot report per-call tokens, calls log
    tokens 'unknown'; the budget still enforces model_calls and wall_time_s, and
    the unknown tokens raise a major (not a blocker)."""
    # Two calls: tokens unknown (default), duration known.
    _log(tmp_path, duration_s=30.0)
    _log(tmp_path, duration_s=45.0)
    usage = c.usage_from_calls(tmp_path)
    assert usage["model_calls"] == 2
    assert usage["tokens"] == "unknown"
    assert usage["wall_time_s"] == 75.0

    # Limits on the known dimensions still bite; tokens-unknown is only a major.
    budget = {"limits": {"model_calls": 10, "wall_time_s": 100, "tokens": 1000}}
    res = c.check(budget, usage)
    assert res["allowed"] is True
    sev = {f["check_id"]: f["severity"] for f in res["findings"]}
    assert sev.get("budget.unknown_usage") == "major"
    assert not any(f["severity"] == "blocker" for f in res["findings"])

    # Exhausted wall-time is a blocker even though tokens are unknown.
    res2 = c.check({"limits": {"model_calls": 10, "wall_time_s": 50}}, usage)
    assert res2["allowed"] is False
    assert any(f["check_id"] == "budget.exhausted" for f in res2["findings"])
