"""Citation binding (M4-16): render [[cite:key]] markers to [N]/[N, loc] and
build a numbered reference list in the references unit, in appearance order."""

from __future__ import annotations

from pathlib import Path

from research_harness.export_docx import assemble, citations, references
from research_harness.sources import registry
from research_harness.structure import model
from research_harness.workspace.objects import create_object
from research_harness.workspace.workspace import Workspace

_INTRO = "U-AAAAAAAA"
_BODY = "U-BBBBBBBB"
_REFS = "U-CCCCCCCC"


def _object(tmp_path: Path):
    ws = Workspace.init(tmp_path / "Projects")
    oid, folder = create_object(ws, title="Цитати", kind="article", document_kind="article")
    model.save(
        folder,
        {
            "schema_version": "0.2",
            "object_id": oid,
            "labels": {},
            "units": [
                {"id": _INTRO, "kind": "introduction", "title": "Вступ"},
                {"id": _BODY, "kind": "section", "title": "Розділ"},
                {"id": _REFS, "kind": "references", "title": "Список використаних джерел"},
            ],
        },
    )
    for sub, uid, title, kind, body in (
        ("a", _INTRO, "Вступ", "introduction", "First point [[cite:smith2020]].\n"),
        (
            "b",
            _BODY,
            "Розділ",
            "section",
            "Earlier [[cite:koval2019|с. 25]]; again [[cite:smith2020]].\n",
        ),
        ("c", _REFS, "Список використаних джерел", "references", ""),
    ):
        (folder / "manuscript" / sub).mkdir(parents=True)
        (folder / "manuscript" / sub / "text.md").write_text(
            f"---\nid: {uid}\ntitle: {title}\nkind: {kind}\n---\n{body}",
            encoding="utf-8",
        )
    return folder


def _sources(folder: Path) -> None:
    registry.add_records(
        folder,
        [
            {
                "bib_key": "smith2020",
                "author": "Smith, J.",
                "title": "On things",
                "container": "Journal",
                "year": "2020",
                "metadata_status": "matched",
            },
            {
                "bib_key": "koval2019",
                "author": "Коваль, І. І.",
                "title": "Про щось",
                "container": "Вісник",
                "year": "2019",
                "metadata_status": "matched",
            },
        ],
    )


def test_markers_render_in_appearance_order(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    _sources(folder)
    md = assemble.assemble_markdown(folder)
    # smith2020 appears first (intro) -> [1]; koval2019 second -> [2].
    assert "First point [1]." in md
    assert "Earlier [2, с. 25]; again [1]." in md
    assert "[[cite:" not in md  # all markers consumed


def test_references_unit_holds_numbered_list(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    _sources(folder)
    md = assemble.assemble_markdown(folder)
    assert "# Список використаних джерел" in md
    assert "1. Smith J. On things. Journal. 2020." in md
    assert "2. Коваль І. І. Про щось. Вісник. 2019." in md


def test_unresolved_key_renders_placeholder_and_is_gap(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    _sources(folder)
    (folder / "manuscript" / "b" / "text.md").write_text(
        f"---\nid: {_BODY}\ntitle: Розділ\nkind: section\n---\nGhost [[cite:ghost9999]].\n",
        encoding="utf-8",
    )
    rendered, _bib, gaps = citations.bind(folder, ["Ghost [[cite:ghost9999]]."])
    assert rendered == ["Ghost [?]."]
    assert any(g["check_id"] == "export.cite_unresolved" for g in gaps)
    # references.build also reports the unresolved key as a blocker gap.
    assert any(g["check_id"] == "export.cite_unresolved" for g in references.build(folder)[1])


def test_locator_not_treated_as_part_of_key(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    _sources(folder)
    # references.build must see "koval2019", not "koval2019|с. 25".
    assert references.cited_keys(folder) == {"smith2020", "koval2019"}
