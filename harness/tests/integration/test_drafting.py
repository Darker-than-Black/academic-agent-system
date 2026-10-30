"""Drafting flow: diff, requested write, conflict refusal, claim rebind (M2-10): T07."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from research_harness.core.errors import BlockedError
from research_harness.units import anchors
from research_harness.units import write as write_mod
from research_harness.workspace.objects import create_object
from research_harness.workspace.workspace import Workspace

_U = "U-AAAAAAAA"


def _object(tmp_path: Path):
    ws = Workspace.init(tmp_path / "Projects")
    _oid, folder = create_object(ws, title="Чернетка", kind="article", document_kind="article")
    uf = folder / "manuscript" / "u1"
    uf.mkdir(parents=True)
    (uf / "text.md").write_text(f"---\nid: {_U}\ntitle: U\nkind: section\n---\n", encoding="utf-8")
    return folder, uf


def test_write_requires_request(tmp_path: Path) -> None:
    folder, _uf = _object(tmp_path)
    with pytest.raises(ValueError):
        write_mod.write_unit(folder, _U, "Some text.", request="")


def test_author_edit_not_overwritten_and_claims_rebind(tmp_path: Path) -> None:  # T07
    folder, uf = _object(tmp_path)
    # Agent drafts two paragraphs.
    write_mod.write_unit(
        folder, _U, "First paragraph.\n\nSecond paragraph.", request="draft the intro"
    )
    base = anchors.paragraph_map(write_mod.read_body(folder, _U))
    pids = list(base)
    p1 = pids[0]

    # A claim bound to the first paragraph.
    from research_harness.units.anchors import paragraph_sha

    (uf / "claims.json").write_text(
        json.dumps(
            {
                "schema_version": "0.2",
                "unit_id": _U,
                "claims": [
                    {"id": "C-1", "location": {"paragraph_id": p1, "text_sha256": "0" * 64}}
                ],
            }
        ),
        encoding="utf-8",
    )

    # Author edits the first paragraph by hand (keeping its anchor).
    author_body = (
        f"<!-- {p1} -->\nFirst paragraph, revised by the author.\n\n"
        f"<!-- {pids[1]} -->\nSecond paragraph."
    )
    write_mod.write_body(folder, _U, author_body, by="author")

    # Claims rebound to the new text of that paragraph.
    claims = json.loads((uf / "claims.json").read_text(encoding="utf-8"))["claims"]
    expected = paragraph_sha(anchors.paragraph_map(write_mod.read_body(folder, _U))[p1])
    assert claims[0]["location"]["text_sha256"] == expected

    # A later agent write that also changes P1, from the stale base, is refused.
    ours = (
        f"<!-- {p1} -->\nFirst paragraph, rewritten by the agent.\n\n"
        f"<!-- {pids[1]} -->\nSecond paragraph."
    )
    with pytest.raises(BlockedError):
        write_mod.write_unit(folder, _U, ours, request="rewrite intro", base=base)

    # The author's version is still on disk (not overwritten).
    assert "revised by the author" in write_mod.read_body(folder, _U)


def test_diff_preview_shows_changes(tmp_path: Path) -> None:
    folder, _uf = _object(tmp_path)
    write_mod.write_unit(folder, _U, "Original.", request="draft")
    d = write_mod.diff_preview(folder, _U, "Rewritten.")
    assert d != "No changes" and "Rewritten" in d
