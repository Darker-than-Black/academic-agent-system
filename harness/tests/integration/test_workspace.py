"""Workspace, author, object folders (01 §4, 02 §3–§4.1, T45)."""

from __future__ import annotations

import json
from pathlib import Path

from research_harness.core.paths import FORBIDDEN_CHARS
from research_harness.workspace import author
from research_harness.workspace.naming import id_from_folder
from research_harness.workspace.objects import create_object, rename_object
from research_harness.workspace.workspace import Workspace
from research_harness_dev.fixtures.f5f import build_f5f


def test_init_workspace_skeleton(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "Projects")
    assert ws.file.is_file()
    assert author.profile_path(ws).is_file()
    assert (author.author_dir(ws) / "publications.bib").is_file()
    assert (author.author_dir(ws) / "corpus" / "index.json").is_file()
    # versions.jsonl has one line per initial file.
    lines = author.versions_path(ws).read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    assert author.read_profile(ws)["name"] == "unknown"


def test_folder_names_follow_rules(tmp_path: Path) -> None:
    root = build_f5f(tmp_path / "Projects")
    folders = [p.name for p in root.iterdir() if p.is_dir() and id_from_folder(p.name)]
    for name in folders:
        human = name.rsplit("__", 1)[0]
        assert not (set(human) & FORBIDDEN_CHARS)
        assert len(human) <= 60
        assert not human.endswith((" ", "."))


def test_pin_is_frozen_until_repin(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "Projects")
    oid, folder = create_object(ws, title="Стаття", kind="article")
    pinned = json.loads((folder / "object.json").read_text(encoding="utf-8"))["author_pins"]

    # Change the author profile after object creation.
    author.set_field(ws, "name", "Автор Тестовий")
    still = json.loads((folder / "object.json").read_text(encoding="utf-8"))["author_pins"]
    assert still == pinned  # object keeps its pinned version and hash

    # Explicit re-pin updates it.
    from research_harness.cli.workspace import _repin

    _repin(ws, folder)
    after = json.loads((folder / "object.json").read_text(encoding="utf-8"))["author_pins"]
    assert after != pinned
    assert after["profile"]["ref"].endswith("@v2")


def test_rename_updates_folder_and_history(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "Projects")
    oid, folder = create_object(ws, title="Старий заголовок", kind="article")
    new_folder = rename_object(ws, oid, "Новий заголовок")
    assert new_folder.is_dir()
    assert not folder.exists()
    obj = json.loads((new_folder / "object.json").read_text(encoding="utf-8"))
    assert obj["title"] == "Новий заголовок"
    assert obj["rename_history"][-1]["from_title"] == "Старий заголовок"
    # Index resolves the id to the new folder.
    assert ws.object_folder(oid) == new_folder


def test_reindex_folders_win(tmp_path: Path) -> None:
    ws = Workspace.init(tmp_path / "Projects")
    oid, _ = create_object(ws, title="Об'єкт", kind="thesis")
    # Corrupt the index, then reindex from disk.
    data = ws.load()
    data["objects"] = []
    ws.save(data)
    objects = ws.reindex()
    assert any(o["id"] == oid for o in objects)
