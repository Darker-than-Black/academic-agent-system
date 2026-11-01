"""`rh budget show|set|check` CLI handler behaviour (M3-01)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import yaml

from research_harness.cli import budget as cli
from research_harness.models import calls


def _args(root: Path, action: str, **kw: object) -> SimpleNamespace:
    base = {
        "object": None,
        "root": str(root),
        "workspace": None,
        "budget_action": action,
        "limit": None,
        "scope": None,
        "paid": None,
        "approval": None,
    }
    base.update(kw)
    return SimpleNamespace(**base)


def _obj(tmp_path: Path) -> Path:
    (tmp_path / ".rh").mkdir()
    return tmp_path


def test_set_then_show(tmp_path: Path) -> None:
    root = _obj(tmp_path)
    env, code = cli.route(
        _args(root, "set", limit=["tokens=1000", "cost=2.5"], scope="object"), "en"
    )
    assert code == 0
    saved = yaml.safe_load((root / "budget.yaml").read_text())
    assert saved["limits"] == {"tokens": 1000, "cost": 2.5}
    assert saved["paid_calls"] == "disabled"

    env, code = cli.route(_args(root, "show"), "en")
    assert code == 0 and env["status"] == "ok"
    assert env["data"]["state"] == "ok"


def test_bad_limit_is_invalid(tmp_path: Path) -> None:
    root = _obj(tmp_path)
    env, code = cli.route(_args(root, "set", limit=["bogus=5"]), "en")
    assert code == 2 and env["status"] == "invalid"


def test_enable_paid_needs_approval(tmp_path: Path) -> None:
    root = _obj(tmp_path)
    env, code = cli.route(_args(root, "set", paid="enabled"), "en")
    assert code == 3 and env["status"] == "blocked"
    assert not (root / "budget.yaml").exists()

    env, code = cli.route(_args(root, "set", paid="enabled", approval="AR-0001"), "en")
    assert code == 0
    saved = yaml.safe_load((root / "budget.yaml").read_text())
    assert saved["paid_calls"] == "enabled" and saved["enabled_by"] == "AR-0001"


def test_check_ok_and_blocked(tmp_path: Path) -> None:
    root = _obj(tmp_path)
    cli.route(_args(root, "set", limit=["model_calls=1"]), "en")

    env, code = cli.route(_args(root, "check"), "en")
    assert code == 0 and env["data"]["allowed"] is True

    calls.log_call(
        root, host="claude-code", role="researcher", tier_required="flagship", model_id="m"
    )
    env, code = cli.route(_args(root, "check"), "en")
    assert code == 3 and env["status"] == "blocked"
    assert env["data"]["allowed"] is False


def test_check_paid_gate_blocks(tmp_path: Path) -> None:
    root = _obj(tmp_path)
    env, code = cli.route(_args(root, "check", paid=True), "en")
    assert code == 3
    assert any(f["check_id"] == "budget.paid_call_disabled" for f in env["findings"])
