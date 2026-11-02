"""P1-1: Codex critic live-subprocess path, proven with a LOCAL STUB codex.

No paid call is made: ``codex`` here is a stub script on PATH emitting canned
JSONL, and the "allowed" budget is injected into the test object root ONLY. The
repo never enables paid_calls (H9/H6).
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

from research_harness.review import engine

_AGENT_JSON = {
    "verdicts": [
        {
            "claim_id": "C-1",
            "support": "supported",
            "rationale": "the excerpt states the claim verbatim",
            "evidence_refs": ["excerpt:E-00001"],
        }
    ],
    "findings": [
        {
            "id": "F-00001",
            "check_id": "critic.manual",
            "severity": "minor",
            "status": "open",
            "location": {"ref": "unit:U-00000001"},
            "observed": "a",
            "expected": "b",
            "reason": "mismatch",
            "evidence_refs": ["excerpt:E-00001"],
            "proposed_action": "revise the sentence",
            "check_run_id": "codex-1",
        }
    ],
}


def _jsonl(agent_text: str, *, failed: bool = False) -> str:
    lines = [
        {"type": "thread.started", "thread_id": "t1"},
        {"type": "turn.started"},
        {"type": "item.completed", "item": {"type": "reasoning", "text": "…"}},
        {"type": "item.completed", "item": {"type": "agent_message", "text": agent_text}},
    ]
    if failed:
        lines.append({"type": "turn.failed", "error": {"message": "boom"}})
    else:
        lines.append(
            {
                "type": "turn.completed",
                "usage": {
                    "input_tokens": 1200,
                    "cached_input_tokens": 0,
                    "output_tokens": 340,
                    "reasoning_output_tokens": 50,
                },
            }
        )
    return "".join(json.dumps(x) + "\n" for x in lines)


def _install_stub(tmp_path: Path, monkeypatch, output: str) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    out_file = tmp_path / "codex_out.jsonl"
    out_file.write_text(output, encoding="utf-8")
    stub = bin_dir / "codex"
    stub.write_text(f'#!/bin/sh\ncat "{out_file}"\n', encoding="utf-8")
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    return out_file


def _allow_budget(root: Path) -> None:
    (root / "budget.yaml").write_text(
        "paid_calls: enabled\nenabled_by: AP-0001\n", encoding="utf-8"
    )


def _calls(root: Path) -> list[dict]:
    p = root / ".rh" / "model-calls.jsonl"
    if not p.is_file():
        return []
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line]


def test_refused_when_paid_calls_disabled(tmp_path: Path, monkeypatch) -> None:
    # No budget.yaml -> paid gate refuses; no subprocess, no model-call logged.
    _install_stub(tmp_path, monkeypatch, _jsonl(json.dumps(_AGENT_JSON)))
    res = engine.run_codex(tmp_path, tmp_path, "review this")
    assert res["status"] == "refused" and res["allowed"] is False
    assert any(f["check_id"] == "budget.paid_call_disabled" for f in res["findings"])
    assert res["verdicts"] == []
    assert _calls(tmp_path) == []  # guard ran before any call (H9)


def test_stub_run_maps_and_logs(tmp_path: Path, monkeypatch) -> None:
    _allow_budget(tmp_path)
    _install_stub(tmp_path, monkeypatch, _jsonl(json.dumps(_AGENT_JSON)))
    res = engine.run_codex(tmp_path, tmp_path, "review this", role="unit_critic")
    assert res["status"] == "ok", res
    assert res["verdicts"][0]["claim_id"] == "C-1"
    assert res["findings"][0]["id"] == "F-00001"
    assert res["schema_errors"] == []
    assert res["model_id"] == "gpt-5-codex"
    # FR-55: model id and token usage logged, tier resolved from roles.yaml.
    calls = _calls(tmp_path)
    assert len(calls) == 1
    rec = calls[0]
    assert rec["model_id"] == "gpt-5-codex"
    assert rec["role"] == "unit_critic" and rec["tier_required"] == "strong"
    assert rec["tokens_in"] == 1200 and rec["tokens_out"] == 340
    assert rec["status"] == "ok"


def test_stub_non_json_message_is_unparsable(tmp_path: Path, monkeypatch) -> None:
    _allow_budget(tmp_path)
    _install_stub(tmp_path, monkeypatch, _jsonl("I could not produce JSON."))
    res = engine.run_codex(tmp_path, tmp_path, "review this")
    assert res["status"] == "unparsable"
    assert res["parse_error"] and "not JSON" in res["parse_error"]
    assert _calls(tmp_path)[0]["status"] == "ok"  # the call itself ran fine


def test_stub_invalid_schema_is_unparsable(tmp_path: Path, monkeypatch) -> None:
    _allow_budget(tmp_path)
    bad = {"verdicts": [{"claim_id": "C-1", "support": "supported"}], "findings": []}
    _install_stub(tmp_path, monkeypatch, _jsonl(json.dumps(bad)))
    res = engine.run_codex(tmp_path, tmp_path, "review this")
    assert res["status"] == "unparsable"  # supported verdict without evidence
    assert res["schema_errors"]


def test_turn_failed_marks_failed(tmp_path: Path, monkeypatch) -> None:
    _allow_budget(tmp_path)
    _install_stub(tmp_path, monkeypatch, _jsonl(json.dumps(_AGENT_JSON), failed=True))
    res = engine.run_codex(tmp_path, tmp_path, "review this")
    assert res["status"] == "failed"
    assert _calls(tmp_path)[0]["status"] == "failed"


def test_missing_codex_binary_fails_gracefully(tmp_path: Path, monkeypatch) -> None:
    _allow_budget(tmp_path)
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))  # no codex anywhere
    res = engine.run_codex(tmp_path, tmp_path, "review this")
    assert res["status"] == "failed"
    assert "subprocess error" in res["reason"]


def test_parse_jsonl_picks_last_agent_message() -> None:
    stream = (
        json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "first"}})
        + "\nnot json at all\n"
        + json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "last"}})
        + "\n"
        + json.dumps({"type": "turn.completed", "usage": {"input_tokens": 5, "output_tokens": 7}})
        + "\n"
    )
    parsed = engine._parse_codex_jsonl(stream)
    assert parsed["agent_text"] == "last"
    assert parsed["usage"]["input_tokens"] == 5
    assert parsed["failed"] is False
