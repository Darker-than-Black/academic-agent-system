"""Intake: unknowns with consequences, prefill, G0 request (T01, T26, T27)."""

from __future__ import annotations

from pathlib import Path

from research_harness.gates.requests import open_requests
from research_harness.intake import answers as answers_mod
from research_harness.intake import questions as questions_mod
from research_harness.intake.flow import apply_answer
from research_harness.workspace import author
from research_harness.workspace.objects import create_object
from research_harness.workspace.workspace import Workspace


def _object(tmp_path: Path, kind: str = "article"):
    ws = Workspace.init(tmp_path / "Projects")
    oid, folder = create_object(ws, title="Тест", kind=kind, document_kind=kind)
    return ws, oid, folder


def test_core_question_count_within_limit() -> None:
    assert questions_mod.core_count() <= 10


def test_unknown_always_has_consequence_and_no_fabrication(tmp_path: Path) -> None:
    _ws, _oid, folder = _object(tmp_path)
    apply_answer(folder, "Q1", "Тема", lang="uk")
    apply_answer(folder, "Q4", answers_mod.UNKNOWN, lang="uk")  # venue unknown
    apply_answer(folder, "Q7", answers_mod.UNKNOWN, lang="uk")  # participants unknown

    data = answers_mod.load(folder)
    unknown_qs = {q for q, e in data["answers"].items() if e["value"] == "unknown"}
    consequence_qs = {c["question"] for c in data["consequences"]}
    assert unknown_qs == consequence_qs  # every unknown has a consequence
    # Q4 unknown blocks A12 and G3 (02 §9.1 example).
    q4 = next(c for c in data["consequences"] if c["question"] == "Q4")
    assert "A12" in q4["blocks"] and "G3" in q4["blocks"]
    # No fabricated value: stored value is exactly "unknown".
    assert data["answers"]["Q4"]["value"] == "unknown"


def test_g0_opens_only_when_intake_complete(tmp_path: Path) -> None:
    _ws, oid, folder = _object(tmp_path)
    core = {
        "Q1": "Тема",
        "Q2": "article",
        "Q3": "uk",
        "Q4": "Journal X",
        "Q5": "literature",
        "Q6": "ua",
        "Q7": "no",
        "Q10": "gates",
    }
    items = list(core.items())
    # No G0 request while core questions remain unanswered (one AR per answer
    # was the bug: each answer snapshots and the per-snapshot reuse misses).
    for qid, value in items[:-1]:
        result = apply_answer(folder, qid, value, lang="uk")
        assert result["g0_request"] is None
        assert not open_requests(folder, "G0")

    last_qid, last_value = items[-1]
    result = apply_answer(folder, last_qid, last_value, lang="uk")
    assert result["g0_request"].startswith("AR-")
    assert len(open_requests(folder, "G0")) == 1  # exactly one, not one per answer
    assert not (folder / "approvals" / "approvals.jsonl").exists()  # no approval recorded


def test_second_object_prefills_author_fields(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "Projects")
    author.set_field(ws, "orcid", "0000-0002-1825-0097")
    author.set_field(ws, "affiliations", ["Synthetic University"])
    create_object(ws, title="Перша", kind="article", document_kind="article")
    _oid, _folder = create_object(ws, title="Друга", kind="article", document_kind="article")

    plan = questions_mod.plan({}, author_profile=author.read_profile(ws))
    asked = {q["id"] for q in plan["ask"]}
    prefilled = {p["id"] for p in plan["prefilled"]}
    assert {"Q8", "Q9", "Q10"} <= prefilled  # ORCID, affiliation, autonomy prefilled
    assert not ({"Q8", "Q9", "Q10"} & asked)  # not asked again
