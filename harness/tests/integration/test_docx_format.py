"""Article .docx format profile (M4-12): reference.docx styles + volume finding."""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

import pytest

from research_harness.export_docx import assemble, format_profile
from research_harness.rules.loader import lint_pack
from research_harness.structure import model
from research_harness.workspace.objects import create_object
from research_harness.workspace.workspace import Workspace

_PACK = Path(__file__).parents[2] / "rulepacks" / "ua-fahove-b"
_REF = _PACK / "reference.docx"

_U = "U-AAAAAAAA"


def _object(tmp_path: Path, body: str):
    ws = Workspace.init(tmp_path / "Projects")
    oid, folder = create_object(ws, title="Формат", kind="article", document_kind="article")
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
    (folder / "manuscript" / "a" / "text.md").write_text(
        f"---\nid: {_U}\ntitle: Розділ\nkind: section\n---\n{body}", encoding="utf-8"
    )
    return folder


def test_reference_docx_encodes_the_profile() -> None:
    z = zipfile.ZipFile(_REF)
    styles = z.read("word/styles.xml").decode()
    doc = z.read("word/document.xml").decode()
    assert "Times New Roman" in styles
    assert 'w:sz w:val="28"' in styles  # 14 pt
    assert 'w:line="360"' in styles  # 1.5 spacing
    assert 'w:firstLine="709"' in styles  # 1.25 cm indent
    assert 'w:top="1134"' in doc and 'w:left="1701"' in doc  # top 2 cm, left 3 cm (МОН)
    assert "tblBorders" in styles  # tables get a full border grid
    assert 'w:w="11906"' in doc  # A4 width
    assert "footerReference" in doc
    assert "PAGE" in z.read("word/footer1.xml").decode()


def test_page_estimate_scales_with_length(tmp_path: Path) -> None:
    folder = _object(tmp_path, "x" * 3600)
    assert format_profile.page_estimate(folder, chars_per_page=1800) >= 2


def test_volume_finding_fires_above_threshold(tmp_path: Path) -> None:
    folder = _object(tmp_path, "слово " * 500)
    over = format_profile.volume_findings(folder, max_pages=1, chars_per_page=100)
    assert over and over[0]["check_id"] == "format.volume"
    assert over[0]["severity"] == "major"
    assert format_profile.volume_findings(folder, max_pages=9999) == []


def test_volume_finding_in_draft_gaps(tmp_path: Path) -> None:
    # > 20 pages at the default 1800 chars/page profile -> format.volume in gaps.
    folder = _object(tmp_path, "а" * 40000)
    gaps = assemble._gaps(folder)
    assert any(g["check_id"] == "format.volume" for g in gaps)

    small = _object(tmp_path / "small", "короткий текст")
    assert not any(g["check_id"] == "format.volume" for g in assemble._gaps(small))


@pytest.mark.skipif(not shutil.which("pandoc"), reason="pandoc not installed")
def test_export_renders_against_reference_docx(tmp_path: Path) -> None:
    folder = _object(tmp_path, "Текст статті для експорту.")
    result = assemble.export_draft(folder, fmt="docx")
    if result["format"] != "docx":
        pytest.skip("pandoc present but docx not produced")
    produced = Path(result["dir"]) / "manuscript.docx"
    styles = zipfile.ZipFile(produced).read("word/styles.xml").decode()
    assert "Times New Roman" in styles and 'w:val="28"' in styles


def test_format_rulepack_lints_clean() -> None:
    assert lint_pack(_PACK) == []
