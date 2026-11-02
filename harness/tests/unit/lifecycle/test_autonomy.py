"""Autonomy level + gate-skip enforcement (M3-06, FR-33)."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from research_harness.cli import autonomy as cli
from research_harness.lifecycle import autonomy as a


def _obj(tmp_path: Path, autonomy: str | None = None) -> Path:
    (tmp_path / ".rh").mkdir()
    obj: dict[str, object] = {"id": "A-2026-001"}
    if autonomy:
        obj["autonomy"] = autonomy
    (tmp_path / "object.json").write_text(json.dumps(obj), encoding="utf-8")
    return tmp_path


def test_default_and_set(tmp_path: Path) -> None:
    root = _obj(tmp_path)
    assert a.read(root) == "gates"
    assert a.set_level(root, "batch") == "batch"
    assert a.read(root) == "batch"


def test_bad_level_raises(tmp_path: Path) -> None:
    root = _obj(tmp_path)
    with pytest.raises(ValueError):
        a.set_level(root, "turbo")


def test_gate_skip_finding() -> None:
    assert a.gate_skip_finding("G1", {"G0", "G1"}) is None
    f = a.gate_skip_finding("G2", {"G0"})
    assert f is not None
    assert f["check_id"] == "lifecycle.autonomy_gate_skip" and f["severity"] == "blocker"


def _args(root: Path, action: str, **kw: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "object": None,
        "root": str(root),
        "workspace": None,
        "autonomy_action": action,
    }
    base.update(kw)
    return SimpleNamespace(**base)


def test_cli_show(tmp_path: Path) -> None:
    root = _obj(tmp_path, "step")
    env, code = cli.route(_args(root, "show"), "en")
    assert code == 0 and env["data"]["autonomy"] == "step"


def test_cli_set_is_human_only(tmp_path: Path) -> None:
    # pytest has no TTY -> is_human_channel() false -> set must be blocked.
    root = _obj(tmp_path, "gates")
    env, code = cli.route(_args(root, "set", level="batch"), "en")
    assert code == 3 and env["status"] == "blocked"
    assert env["next_actions"][0]["who"] == "author"
    assert a.read(root) == "gates"  # unchanged
