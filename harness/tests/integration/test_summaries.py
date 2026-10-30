"""Summaries, map, glossary, staleness (M2-08): T51."""

from __future__ import annotations

from pathlib import Path

import pytest

from research_harness.core.errors import BlockedError
from research_harness.structure import model
from research_harness.summaries import deterministic as det_mod
from research_harness.summaries import glossary as glossary_mod
from research_harness.summaries import map as map_mod
from research_harness.summaries import semantic as semantic_mod
from research_harness.workspace.objects import create_object
from research_harness.workspace.workspace import Workspace

_UA = "U-AAAAAAAA"
_UB = "U-BBBBBBBB"


def _text(uid: str, title: str, body: str) -> str:
    return f"---\nid: {uid}\ntitle: {title}\nkind: subsection\n---\n{body}\n"


def _object(tmp_path: Path):
    ws = Workspace.init(tmp_path / "Projects")
    _oid, folder = create_object(ws, title="Конспекти", kind="thesis", document_kind="thesis")
    structure = {
        "schema_version": "0.2",
        "object_id": _oid,
        "labels": {},
        "units": [
            {
                "id": "CH-1",
                "kind": "chapter",
                "title": "Розділ",
                "children": [
                    {"id": _UA, "kind": "subsection", "title": "A"},
                    {"id": _UB, "kind": "subsection", "title": "B"},
                ],
            }
        ],
    }
    model.save(folder, structure)
    (folder / "manuscript" / "ch1" / "s1").mkdir(parents=True)
    (folder / "manuscript" / "ch1" / "s2").mkdir(parents=True)
    (folder / "manuscript" / "ch1" / "s1" / "text.md").write_text(
        _text(_UA, "A", "Intro paragraph with @smith2020 and 42 items."), encoding="utf-8"
    )
    (folder / "manuscript" / "ch1" / "s2" / "text.md").write_text(
        _text(_UB, "B", "Second unit body."), encoding="utf-8"
    )
    return folder


def test_build_then_change_propagates_staleness(tmp_path: Path) -> None:  # T51
    folder = _object(tmp_path)
    map_mod.build(folder)
    assert map_mod.map_path(folder).is_file()
    assert not map_mod.anything_stale(folder)

    before = det_mod.load_summary(folder / "manuscript" / "ch1" / "s2")["deterministic"]

    # Change the text of unit B.
    (folder / "manuscript" / "ch1" / "s2" / "text.md").write_text(
        _text(_UB, "B", "A much longer second unit body with more content added here."),
        encoding="utf-8",
    )

    report = map_mod.stale_report(folder)
    assert report[_UB] is True  # changed unit
    assert report[_UA] is False  # untouched unit
    assert report["CH-1"] is True  # its chapter
    assert report["map"] is True  # the document map

    # Integration-level action on stale summaries is refused.
    with pytest.raises(BlockedError):
        map_mod.require_fresh(folder)

    # Rebuild recomputes the deterministic part.
    map_mod.build(folder)
    after = det_mod.load_summary(folder / "manuscript" / "ch1" / "s2")["deterministic"]
    assert after["chars_with_spaces"] != before["chars_with_spaces"]
    assert not map_mod.anything_stale(folder)


def test_semantic_survives_only_for_its_hash(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    det_mod.build_unit(folder, _UA)
    summary, findings = semantic_mod.set_semantic(
        folder, _UA, main_thesis="A introduces the problem.", key_claims=[], language="uk"
    )
    assert not findings and summary["semantic"]["main_thesis"]

    # Rebuild with unchanged text keeps the semantic part.
    det_mod.build_unit(folder, _UA)
    assert det_mod.load_summary(folder / "manuscript" / "ch1" / "s1").get("semantic")

    # Change the text: the semantic part is dropped (hash no longer matches).
    (folder / "manuscript" / "ch1" / "s1" / "text.md").write_text(
        _text(_UA, "A", "Rewritten."), encoding="utf-8"
    )
    det_mod.build_unit(folder, _UA)
    assert not det_mod.load_summary(folder / "manuscript" / "ch1" / "s1").get("semantic")


def test_glossary_checks(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    glossary_mod.add_term(folder, term="validity", definition="truth of inference", source="author")
    # Alias conflict: another term claims the same alias.
    glossary_mod.add_term(
        folder, term="reliability", definition="consistency", source="author", aliases=["validity"]
    )
    # A text referencing an undefined term.
    (folder / "manuscript" / "ch1" / "s1" / "text.md").write_text(
        _text(_UA, "A", "We use {{term:bias}} here."), encoding="utf-8"
    )
    findings = glossary_mod.check(folder)
    ids = {f["check_id"] for f in findings}
    assert "glossary.alias_conflict" in ids
    assert "glossary.term_undefined" in ids
