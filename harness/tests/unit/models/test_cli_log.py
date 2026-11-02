"""P1-3: `rh model log` records a measured --duration-s (wall-time budgeting)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from research_harness.cli import models as cli


def _args(root: Path, **kw: object) -> SimpleNamespace:
    base = {
        "object": None,
        "root": str(root),
        "workspace": None,
        "model_action": "log",
        "role": "writer",
        "model": "claude-opus-5-5",
        "host": "claude-code",
        "tokens_in": None,
        "tokens_out": None,
        "cost": None,
        "duration_s": None,
        "purpose": None,
        "status": "ok",
    }
    base.update(kw)
    return SimpleNamespace(**base)


def test_log_records_duration_tokens_unknown(tmp_path: Path) -> None:
    (tmp_path / ".rh").mkdir()
    env, code = cli.route(_args(tmp_path, duration_s=12.5), "en")
    assert code == 0
    rec = env["data"]["call"]
    assert rec["duration_s"] == 12.5
    # No tokens supplied -> unknown, never guessed or zeroed (H7).
    assert rec["tokens_in"] == "unknown" and rec["tokens_out"] == "unknown"


def test_log_without_duration_is_unknown(tmp_path: Path) -> None:
    (tmp_path / ".rh").mkdir()
    env, code = cli.route(_args(tmp_path), "en")
    assert code == 0
    assert env["data"]["call"]["duration_s"] == "unknown"
