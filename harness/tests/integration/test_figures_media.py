"""Figures in articles (M4-14): placement, numbering, caption, ref checks."""

from __future__ import annotations

from pathlib import Path

from research_harness.analysis import figures
from research_harness.export_docx import assemble, figures_embed
from research_harness.structure import model
from research_harness.workspace.objects import create_object
from research_harness.workspace.workspace import Workspace

_U = "U-AAAAAAAA"


def _object(tmp_path: Path):
    ws = Workspace.init(tmp_path / "Projects")
    oid, folder = create_object(ws, title="Фігури", kind="article", document_kind="article")
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


def _body(folder: Path, text: str) -> None:
    (folder / "manuscript" / "a" / "text.md").write_text(
        f"---\nid: {_U}\ntitle: Розділ\nkind: section\n---\n{text}", encoding="utf-8"
    )


def _add_figure(folder: Path, caption: str, *, alt: str = "", build: bool = True) -> str:
    script = folder / "plot.py"
    script.write_text("# plotting script\n", encoding="utf-8")
    rec = figures.add(folder, script="plot.py", row_ids=[], fmt="svg", caption=caption, alt=alt)
    if build:  # simulate a built image without running the sandbox
        figures.image_path(folder, rec["id"]).write_bytes(b"<svg/>")
    return rec["id"]


def test_marker_renders_image_and_numbered_caption(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    fid = _add_figure(folder, "Розподіл залученості", alt="стовпчикова діаграма")
    _body(folder, f"Дивись {{{{fig:{fid}}}}} нижче.")
    md = assemble.assemble_markdown(folder)
    assert "Рис. 1. Розподіл залученості" in md
    assert "![стовпчикова діаграма](" in md
    assert "{{fig:" not in md


def test_unresolved_marker_is_a_gap(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    _body(folder, "Текст {{fig:FIG-999}}.")
    rendered, gaps = figures_embed.bind(folder, ["Текст {{fig:FIG-999}}."])
    assert "[рисунок відсутній]" in rendered[0]
    assert any(g["check_id"] == "figure.unresolved_ref" for g in gaps)


def test_unreferenced_figure_is_a_gap(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    _add_figure(folder, "Неразміщена")
    _body(folder, "Текст без посилання на рисунок.")
    gaps = assemble._gaps(folder)
    assert any(g["check_id"] == "figure.unreferenced" for g in gaps)


def test_placed_but_unbuilt_figure_is_a_gap(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    fid = _add_figure(folder, "Ще не збудована", build=False)
    _body(folder, f"{{{{fig:{fid}}}}}")
    rendered, gaps = figures_embed.bind(folder, [f"{{{{fig:{fid}}}}}"])
    assert "Рис. 1. Ще не збудована" in rendered[0]  # caption renders without the image
    assert any(g["check_id"] == "figure.not_built" for g in gaps)


def test_numbering_follows_appearance(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    f1 = _add_figure(folder, "Перша")
    f2 = _add_figure(folder, "Друга")
    rendered, _ = figures_embed.bind(folder, [f"{{{{fig:{f2}}}}} then {{{{fig:{f1}}}}}"])
    # f2 appears first -> Рис. 1; f1 second -> Рис. 2.
    assert "Рис. 1. Друга" in rendered[0]
    assert "Рис. 2. Перша" in rendered[0]
