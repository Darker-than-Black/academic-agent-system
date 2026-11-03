"""Substance report (M4-15): weak material-claim deficits + analysis-free signal."""

from __future__ import annotations

from pathlib import Path

from research_harness.claims import ledger as ledger_mod
from research_harness.rules.loader import lint_pack
from research_harness.structure import model
from research_harness.substance import report as report_mod
from research_harness.workspace.objects import create_object
from research_harness.workspace.workspace import Workspace

_U = "U-AAAAAAAA"
_PACK = Path(__file__).parents[2] / "rulepacks" / "ua-fahove-b"


def _object(tmp_path: Path):
    ws = Workspace.init(tmp_path / "Projects")
    oid, folder = create_object(ws, title="Суть", kind="article", document_kind="article")
    model.save(
        folder,
        {
            "schema_version": "0.2",
            "object_id": oid,
            "labels": {},
            "units": [{"id": _U, "kind": "section", "title": "Розділ"}],
        },
    )
    (folder / "manuscript" / "a").mkdir(parents=True)
    return folder


def _write_body(folder: Path, body: str) -> None:
    (folder / "manuscript" / "a" / "text.md").write_text(
        f"---\nid: {_U}\ntitle: Розділ\nkind: section\n---\n{body}",
        encoding="utf-8",
    )


def test_weak_material_claim_is_a_deficit(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    ledger_mod.set_claims(
        folder,
        _U,
        [
            {
                "text": "Гейміфікація підвищує залученість.",
                "kind": "external",
                "materiality": "material",
            }
        ],
    )
    findings = report_mod.material_deficits(folder)
    assert len(findings) == 1
    f = findings[0]
    assert f["check_id"] == "substance.material_claim_deficit"
    assert f["severity"] == "major"
    assert f["observed"] == "unreviewed"
    assert f["proposed_action"]  # tells the author what to supply


def test_background_claim_is_not_a_deficit(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    ledger_mod.set_claims(
        folder, _U, [{"text": "Побіжна примітка.", "kind": "external", "materiality": "background"}]
    )
    assert report_mod.material_deficits(folder) == []


def test_analysis_free_warns_on_mostly_limitations(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    _write_body(
        folder,
        "Дані не містять потрібної змінної. Не вдалося перевірити гіпотезу. "
        "Бракує емпіричних даних. Гейміфікація застосовується широко.",
    )
    findings, data = report_mod.analysis_free_signal(folder)
    assert data["sentences"] == 4
    assert data["limitation_sentences"] == 3
    assert findings and findings[0]["check_id"] == "substance.analysis_free"
    assert findings[0]["severity"] == "major"


def test_analysis_free_quiet_on_normal_text(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    _write_body(
        folder,
        "Гейміфікація підвищує мотивацію. Дизайн механік визначає ефект. "
        "Крос-аналіз джерел показує узгоджений патерн. Результати стійкі.",
    )
    findings, data = report_mod.analysis_free_signal(folder)
    assert data["limitation_sentences"] == 0
    assert findings == []


def test_build_carries_author_next_actions(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    ledger_mod.set_claims(
        folder, _U, [{"text": "Суттєве твердження.", "kind": "external", "materiality": "material"}]
    )
    _write_body(folder, "Не вдалося провести аналіз. Бракує даних.")
    findings, data, next_actions = report_mod.build(folder)
    assert data["material_claims_weak"] == 1
    assert data["analysis_free"] is True
    assert next_actions and all(a["who"] == "author" for a in next_actions)


def test_substance_rulepack_lints_clean() -> None:
    assert lint_pack(_PACK) == []
