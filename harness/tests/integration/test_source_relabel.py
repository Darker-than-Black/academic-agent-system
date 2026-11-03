"""`rh source relabel` — set a unique, cite-safe citation key (M4-16 enabler)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from research_harness.cli import sources as sources_cli
from research_harness.core.errors import InvalidInputError
from research_harness.sources import registry
from research_harness.workspace.objects import create_object
from research_harness.workspace.workspace import Workspace


def _object(tmp_path: Path):
    ws = Workspace.init(tmp_path / "Projects")
    _oid, folder = create_object(ws, title="Дж", kind="article", document_kind="article")
    registry.add_records(
        folder,
        [
            {"bib_key": "doi1", "title": "A", "doi": "10.1/a"},
            {"bib_key": "doi1", "title": "B", "doi": "10.1/b"},
        ],
    )
    return folder


def _args(folder: Path, sid: str, key: str):
    return SimpleNamespace(
        source_action="relabel", id=sid, bib_key=key, root=str(folder), object=None
    )


def test_relabel_sets_unique_key(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    env, code = sources_cli.route(_args(folder, "S-0001", "meng2024"), "en")
    assert code == 0 and env["status"] == "ok"
    assert registry.get(folder, "S-0001")["bib_key"] == "meng2024"


def test_relabel_rejects_duplicate_key(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    # S-0002 still has doi1; relabel S-0001 to doi1 clashes.
    env, code = sources_cli.route(_args(folder, "S-0001", "doi1"), "en")
    assert code == 3 and env["status"] == "blocked"
    assert any(f["check_id"] == "source.bib_key_taken" for f in env["findings"])


def test_relabel_rejects_invalid_key(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    env, code = sources_cli.route(_args(folder, "S-0001", "bad key!"), "en")
    assert code == 3 and env["status"] == "blocked"
    assert any(f["check_id"] == "source.bib_key_invalid" for f in env["findings"])


def test_relabel_unknown_source_raises(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    with pytest.raises(InvalidInputError):
        sources_cli.route(_args(folder, "S-9999", "x2020"), "en")
