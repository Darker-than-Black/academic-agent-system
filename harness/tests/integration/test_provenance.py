"""Paragraph provenance and dictation (M2-10): T57, T58 (recording)."""

from __future__ import annotations

from pathlib import Path

from research_harness.provenance import dictation as dict_mod
from research_harness.provenance import paragraphs as prov_mod
from research_harness.units import anchors
from research_harness.units import write as write_mod
from research_harness.workspace.objects import create_object
from research_harness.workspace.workspace import Workspace

_U = "U-AAAAAAAA"


def _object(tmp_path: Path):
    ws = Workspace.init(tmp_path / "Projects")
    _oid, folder = create_object(ws, title="Провенанс", kind="article", document_kind="article")
    uf = folder / "manuscript" / "u1"
    uf.mkdir(parents=True)
    (uf / "text.md").write_text(f"---\nid: {_U}\ntitle: U\nkind: section\n---\n", encoding="utf-8")
    return folder, uf


def test_dictation_keeps_raw_and_marks_author(tmp_path: Path) -> None:  # T57
    folder, _uf = _object(tmp_path)
    raw = "Formative assessment helps. It gives feedback. Students improve."
    result = dict_mod.import_transcript(folder, _U, raw, audio_ref="rec-1")
    assert (folder / result["raw_path"]).is_file()  # raw transcript kept

    structured = "Formative assessment helps.\n\nIt gives feedback. Students improve."
    dict_mod.accept_structuring(folder, _U, structured)
    shares = prov_mod.shares(folder, _U)
    assert shares["author"] == 2 and shares["agent"] == 0  # dictated paragraphs are the author's

    share = dict_mod.preserved_phrase_share(raw, structured)
    assert 0.0 <= share <= 1.0 and share > 0.5  # wording preserved


def test_recording_mixed_origins(tmp_path: Path) -> None:  # T58
    folder, _uf = _object(tmp_path)
    # Two dictated (author) paragraphs.
    dict_mod.accept_structuring(folder, _U, "Dictated one.\n\nDictated two.")
    body = write_mod.read_body(folder, _U)
    pmap = anchors.paragraph_map(body)
    d1, d2 = list(pmap)

    # Agent adds three more paragraphs (the dictated two are unchanged).
    agent_body = (
        f"<!-- {d1} -->\nDictated one.\n\n<!-- {d2} -->\nDictated two.\n\n"
        "Agent three.\n\nAgent four.\n\nAgent five."
    )
    write_mod.write_unit(folder, _U, agent_body, request="extend the unit")
    pmap = anchors.paragraph_map(write_mod.read_body(folder, _U))
    ids = list(pmap)
    a3, a4, a5 = ids[2], ids[3], ids[4]

    # Author edits two of the agent paragraphs (-> agent_edited_by_author); one stays agent.
    edited = (
        f"<!-- {d1} -->\nDictated one.\n\n<!-- {d2} -->\nDictated two.\n\n"
        f"<!-- {a3} -->\nAgent three, revised.\n\n<!-- {a4} -->\nAgent four, revised.\n\n"
        f"<!-- {a5} -->\nAgent five."
    )
    write_mod.write_body(folder, _U, edited, by="author")

    shares = prov_mod.shares(folder, _U)
    assert shares["author"] == 2
    assert shares["agent_edited_by_author"] == 2
    assert shares["agent"] == 1
    assert prov_mod.object_shares(folder)["author"] == 2
