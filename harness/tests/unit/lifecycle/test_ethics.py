"""Ethics gate GE enforcement (M3-07, FR-31, T33)."""

from __future__ import annotations

import json
from pathlib import Path

from research_harness.gates.records import approvals_path
from research_harness.lifecycle import ethics as e


def _data(**q: object) -> dict:
    return {"answers": {k: {"value": v} for k, v in q.items()}}


def test_requires_ethics_rules() -> None:
    assert e.requires_ethics(_data(Q7=True)) is True
    assert e.requires_ethics(_data(Q7=False)) is False
    # unknown participants + empirical kind -> required
    assert e.requires_ethics(_data(Q5="empirical_qualitative")) is True
    assert e.requires_ethics(_data(Q7="unknown", Q5="mixed")) is True
    # unknown participants + non-empirical -> not required
    assert e.requires_ethics(_data(Q5="literature")) is False


def _approval(root: Path, **kw: object) -> None:
    rec = {
        "gate": "GE",
        "decision": "approved",
        "actor_role": "ethics_committee",
        "document": {"stored": True, "ref": "ethics/approval.pdf"},
    }
    rec.update(kw)
    p = approvals_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")


def test_has_ethics_approval(tmp_path: Path) -> None:
    assert e.has_ethics_approval(tmp_path) is False  # no file
    _approval(tmp_path)
    assert e.has_ethics_approval(tmp_path) is True


def test_approval_needs_committee_and_document(tmp_path: Path) -> None:
    _approval(tmp_path, actor_role="author")  # wrong role
    assert e.has_ethics_approval(tmp_path) is False
    _approval(tmp_path, document=None)  # no document (overwrites nothing; appended)
    assert e.has_ethics_approval(tmp_path) is False


def test_finding_present_when_required_and_unapproved(tmp_path: Path) -> None:
    from research_harness.intake import answers as am

    am.record(tmp_path, "Q7", True)
    f = e.ethics_gate_finding(tmp_path)
    assert f is not None and f["check_id"] == "lifecycle.ethics_missing"
    _approval(tmp_path)
    assert e.ethics_gate_finding(tmp_path) is None


def test_no_finding_when_not_required(tmp_path: Path) -> None:
    from research_harness.intake import answers as am

    am.record(tmp_path, "Q7", False)
    assert e.ethics_gate_finding(tmp_path) is None
