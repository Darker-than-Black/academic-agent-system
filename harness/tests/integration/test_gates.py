"""Gates and approvals: human-only records, external documents, validity (T37)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from research_harness.cli import gates as cli_gates
from research_harness.core.errors import InvalidInputError
from research_harness.gates import briefing, interactive, records, requests
from research_harness.gates.interactive import confirmation_code, run_record
from research_harness.intake.flow import apply_answer
from research_harness.state import freshness
from research_harness.state.store import Store
from research_harness.workspace.objects import create_object
from research_harness.workspace.workspace import Workspace


def _object(tmp_path: Path):
    ws = Workspace.init(tmp_path / "Projects")
    oid, folder = create_object(ws, title="Гейти", kind="article", document_kind="article")
    apply_answer(folder, "Q1", "Тема", lang="uk")  # opens the G0 request
    return oid, folder


def _args(**kw):
    base = dict(
        gate_action="record",
        gate="G0",
        decision=None,
        reason=None,
        conditions=None,
        actor_role="author",
        actor_label=None,
        document=None,
    )
    base.update(kw)
    return SimpleNamespace(**base)


# --- non-interactive author path -------------------------------------------


def test_non_interactive_record_blocks(tmp_path: Path, monkeypatch) -> None:
    _oid, folder = _object(tmp_path)
    monkeypatch.setattr(interactive, "is_human_channel", lambda: False)
    env, code = cli_gates._record(folder, _args(), "uk")
    assert code == 3 and env["status"] == "blocked"
    assert env["next_actions"][0]["who"] == "author"
    assert "gate record G0" in env["next_actions"][0]["command"]
    assert env["data"]["briefing_path"].endswith(".md")
    assert not records.approvals_path(folder).exists()  # nothing recorded
    assert requests.open_requests(folder, "G0")  # request still open


def test_agent_session_refused_even_on_tty(monkeypatch) -> None:
    monkeypatch.setenv("RH_AGENT_SESSION", "1")
    monkeypatch.setattr("sys.stdin.isatty", lambda: True, raising=False)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True, raising=False)
    assert interactive.is_human_channel() is False


# --- external roles ---------------------------------------------------------


def test_external_role_without_document_is_invalid(tmp_path: Path) -> None:
    _oid, folder = _object(tmp_path)
    with pytest.raises(InvalidInputError):
        cli_gates._record(folder, _args(actor_role="supervisor", decision="approved"), "uk")


def test_external_role_with_document_records(tmp_path: Path, monkeypatch) -> None:
    _oid, folder = _object(tmp_path)
    monkeypatch.setattr(interactive, "is_human_channel", lambda: True)
    doc = tmp_path / "ethics.pdf"
    doc.write_bytes(b"%PDF synthetic approval\n")
    env, code = cli_gates._record(
        folder,
        _args(gate="GE", actor_role="ethics_committee", decision="approved", document=str(doc)),
        "uk",
    )
    assert code == 0
    ap = env["data"]["approval"]
    assert ap["actor_role"] == "ethics_committee"
    assert ap["channel"] == "external_document"
    assert ap["document"]["sha256"]


# --- interactive flow -------------------------------------------------------


def test_wrong_code_records_nothing(tmp_path: Path) -> None:
    _oid, folder = _object(tmp_path)
    inputs = iter(["1", "G0-000000", "G0-111111", "G0-222222"])
    rec = run_record(
        folder, "G0", "uk", input_fn=lambda _p: next(inputs), output_fn=lambda _s: None
    )
    assert rec is None
    assert not records.approvals_path(folder).exists()


def test_reject_requires_reason(tmp_path: Path) -> None:
    _oid, folder = _object(tmp_path)
    target = requests.current_target(folder)
    code = confirmation_code("G0", target["manifest_sha256"])
    # decision reject, empty reason (reprompt), then a reason, then the code.
    inputs = iter(["2", "", "not ready yet", code])
    rec = run_record(
        folder, "G0", "uk", input_fn=lambda _p: next(inputs), output_fn=lambda _s: None
    )
    assert rec is not None and rec["decision"] == "rejected" and rec["reason"] == "not ready yet"


def test_approval_invalid_after_content_change(tmp_path: Path) -> None:
    _oid, folder = _object(tmp_path)
    target = requests.current_target(folder)
    code = confirmation_code("G0", target["manifest_sha256"])
    inputs = iter(["1", code])
    rec = run_record(
        folder, "G0", "uk", input_fn=lambda _p: next(inputs), output_fn=lambda _s: None
    )
    assert freshness.approval_valid(folder, rec) is True

    (folder / "text" / "note.md").parent.mkdir(parents=True, exist_ok=True)
    (folder / "text" / "note.md").write_text("later change\n", encoding="utf-8")
    Store(folder).checkpoint(by="human", note="edit")
    assert freshness.approval_valid(folder, rec) is False


# --- briefing layout --------------------------------------------------------


@pytest.mark.parametrize("lang", ["uk", "en"])
def test_g0_briefing_has_all_layout_elements(tmp_path: Path, lang: str) -> None:
    _oid, folder = _object(tmp_path)
    text = briefing.render(folder, "G0", lang)
    labels = briefing._L[lang]
    for key in ("deciding", "approving", "check", "consequences", "reversible", "how"):
        assert labels[key] in text
    assert "gate record G0" in text  # the exact recording command
    assert "intake/summary.md" in text  # link to the summary
