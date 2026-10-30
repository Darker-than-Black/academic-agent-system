"""Structure tree, renumbering and crash recovery (02 §7, T50)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from research_harness.state.recovery import recover
from research_harness.structure import model, ops
from research_harness.structure.checks import check_structure
from research_harness_dev.fixtures.f7_structure import (
    CH1,
    CH2,
    CH3,
    build_f7_article,
    build_f7_structure,
)


def _dir(folder: Path, rel: str) -> bool:
    return (folder / "manuscript" / rel).is_dir()


def _fm_id(folder: Path, rel: str) -> str:
    text = (folder / "manuscript" / rel / "text.md").read_text(encoding="utf-8")
    return ops._front_matter(text)["id"]


def test_build_is_clean(tmp_path: Path) -> None:
    folder = build_f7_structure(tmp_path / "f7")
    assert check_structure(folder, "uk") == []
    assert _dir(folder, "01 Вступ")
    assert _dir(folder, "02 Розділ 1. Перший розділ/1.4 Підрозділ 4")
    assert _dir(folder, "02 Розділ 1. Перший розділ/1.5 Висновки до розділу 1")


def test_swap_insert_renumber(tmp_path: Path) -> None:
    folder = build_f7_structure(tmp_path / "f7")
    # Swap chapters 2 and 3: move CH3 to the index CH2 held.
    ops.move(folder, CH3, 2, "uk")
    # Insert a subsection after 1.2 in chapter 1 (index 2 among CH1's children).
    ops.add_unit(
        folder,
        kind="subsection",
        title="Новий підрозділ",
        parent_id=CH1,
        index=2,
        main_language="uk",
    )
    ops.renumber(folder, "uk")

    assert check_structure(folder, "uk") == []
    # Chapter 1 renumbered with the inserted subsection.
    assert _dir(folder, "02 Розділ 1. Перший розділ/1.3 Новий підрозділ")
    assert _dir(folder, "02 Розділ 1. Перший розділ/1.6 Висновки до розділу 1")
    # CH3 is now chapter 2 at top position 3; CH2 is now chapter 3 at position 4.
    assert _dir(folder, "03 Розділ 2. Третій розділ/2.4 Висновки до розділу 2")
    assert _dir(folder, "04 Розділ 3. Другий розділ/3.4 Висновки до розділу 3")
    # Front-matter IDs are unchanged by renaming.
    assert _fm_id(folder, "04 Розділ 3. Другий розділ") == CH2
    # A ref to the moved unit still resolves (by id).
    labels = model.resolve_labels(model.load(folder), "uk")
    from research_harness.structure.naming import compute_paths

    assert CH2 in compute_paths(model.parse_units(model.load(folder)), labels)


WORKER = """
import sys
from pathlib import Path
from research_harness_dev.fixtures.f7_structure import build_f7_structure, CH3
from research_harness.structure import ops
folder = build_f7_structure(Path(sys.argv[1]))
ops.move(folder, CH3, 2, "uk")
"""


def test_crash_between_rename_phases_recovers(tmp_path: Path) -> None:
    worker = tmp_path / "w.py"
    worker.write_text(WORKER, encoding="utf-8")
    target = tmp_path / "f7"
    env = {
        **os.environ,
        "RH_TEST_MODE": "1",
        "RH_FAULT_AT": "structure_rename_phase2",
        "RH_FAULT_KILL": "1",
    }
    proc = subprocess.run([sys.executable, str(worker), str(target)], env=env, capture_output=True)
    assert proc.returncode == 99
    obj_root = next(p for p in target.iterdir() if p.is_dir() and "__T-" in p.name)
    assert (obj_root / ".rh" / "structure-journal.json").exists()
    recover(obj_root, repair=True)
    assert not (obj_root / ".rh" / "structure-journal.json").exists()
    # No missing-folder findings: the tree is consistent with structure.yaml.
    majors = [f for f in check_structure(obj_root, "uk") if f["severity"] in ("major", "blocker")]
    assert majors == []


def test_article_depth1_same_code(tmp_path: Path) -> None:
    folder = build_f7_article(tmp_path / "art")
    assert check_structure(folder, "uk") == []
    assert _dir(folder, "01 Секція 1")
    ops.move(folder, "U-10000003", 0, "uk")
    ops.renumber(folder, "uk")
    assert check_structure(folder, "uk") == []
    assert _dir(folder, "01 Секція 3")
