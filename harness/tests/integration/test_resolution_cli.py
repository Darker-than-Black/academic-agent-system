"""rh findings / rh dispute CLI: human-only guard on resolve/close (M3-05, H14)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from research_harness.cli import resolution as cli
from research_harness.findings import index as fi
from research_harness.review import disputes as d


def _obj(tmp_path: Path) -> Path:
    (tmp_path / ".rh").mkdir()
    return tmp_path


def _args(root: Path, command: str, **kw: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "object": None,
        "root": str(root),
        "workspace": None,
        "command": command,
        "findings_action": None,
        "dispute_action": None,
    }
    base.update(kw)
    return SimpleNamespace(**base)


def test_findings_list_ok(tmp_path: Path) -> None:
    root = _obj(tmp_path)
    fi.add(root, {"check_id": "fulltext.crossref", "severity": "blocker", "reason": "x"})
    env, code = cli.findings_list(root, _args(root, "findings", status=None), "en")
    assert code == 0 and len(env["data"]["findings"]) == 1


def test_resolve_blocked_in_agent_channel(tmp_path: Path) -> None:
    # pytest has no TTY, so is_human_channel() is false: resolve must not apply.
    root = _obj(tmp_path)
    fi.add(root, {"check_id": "c", "severity": "major", "reason": "x"})
    args = _args(root, "findings", finding_id="F-1", decision="accept", reason=None)
    env, code = cli.findings_resolve(root, args, "en")
    assert code == 3 and env["status"] == "blocked"
    assert env["next_actions"][0]["who"] == "author"
    assert fi.list_findings(root)[0]["status"] == "open"  # nothing written


def test_dispute_open_and_add_then_close_resolved_is_human_only(tmp_path: Path) -> None:
    root = _obj(tmp_path)
    env, code = cli.route(
        _args(root, "dispute", dispute_action="open", claim="C-1", finding="F-1", max_cycles=2),
        "en",
    )
    assert code == 0 and env["data"]["dispute"]["id"] == "D-1"
    env, code = cli.route(
        _args(
            root,
            "dispute",
            dispute_action="add-evidence",
            dispute_id="D-1",
            by="analyst",
            argument="a",
            evidence=["excerpt:E1"],
        ),
        "en",
    )
    assert code == 0 and len(env["data"]["dispute"]["cycles"]) == 1
    # resolved_by_author is human-only -> blocked in agent channel, dispute stays open.
    env, code = cli.route(
        _args(
            root,
            "dispute",
            dispute_action="close",
            dispute_id="D-1",
            status="resolved_by_author",
            author_decision=None,
        ),
        "en",
    )
    assert code == 3 and env["status"] == "blocked"
    assert d.load(root, "D-1")["status"] == "open"


def test_dispute_close_unresolved_allowed(tmp_path: Path) -> None:
    root = _obj(tmp_path)
    d.open_(root, claim_id="C-1", finding_id="F-1")
    env, code = cli.route(
        _args(
            root,
            "dispute",
            dispute_action="close",
            dispute_id="D-1",
            status="unresolved",
            author_decision=None,
        ),
        "en",
    )
    assert code == 0 and d.load(root, "D-1")["status"] == "unresolved"
