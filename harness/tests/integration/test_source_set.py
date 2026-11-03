"""`rh source set` — author-attested source metadata (M4-13/M4-17 enabler).

Covers: setting a language clears nothing by itself but persists; supplying a
title + author on an unresolved record flips metadata_status to
``author_provided`` and records an author attestation; empty patch and unknown
source are refused.
"""

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
            {"title": "A", "doi": "10.1/a", "metadata_status": "matched"},
            {"title": "", "metadata_status": "unresolved"},
            {
                "title": "Garbled",
                "authors": [{"family": "junk}"}],
                "metadata_status": "unresolved",
            },
        ],
    )
    return folder


def _args(folder: Path, sid: str, **kw):
    base = dict(
        source_action="set",
        id=sid,
        language=None,
        publication_country=None,
        title=None,
        year=None,
        container=None,
        type=None,
        authors=None,
        unresolve=False,
        clear_authors=False,
        root=str(folder),
        object=None,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_set_language_persists(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    env, code = sources_cli.route(_args(folder, "S-0001", language="en"), "en")
    assert code == 0 and env["status"] == "ok"
    assert registry.get(folder, "S-0001")["language"] == "en"


def test_set_country_and_year(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    env, code = sources_cli.route(
        _args(folder, "S-0001", publication_country="GB", year=2024), "en"
    )
    assert code == 0
    rec = registry.get(folder, "S-0001")
    assert rec["publication_country"] == "GB" and rec["year"] == 2024


def test_set_title_author_marks_author_provided(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    env, code = sources_cli.route(
        _args(
            folder,
            "S-0002",
            title="Національний звіт",
            authors=["МОН України, ", "Іваненко, П. П."],
            year=2023,
            language="uk",
        ),
        "en",
    )
    assert code == 0 and env["status"] == "ok"
    rec = registry.get(folder, "S-0002")
    assert rec["metadata_status"] == "author_provided"
    assert rec["authors"][0]["family"] == "МОН України"
    assert rec["authors"][1] == {"family": "Іваненко", "given": "П. П."}
    assert rec["metadata_sources"][-1]["resource"] == "author"


def test_set_keeps_matched_status(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    # Already matched; adding a language must not downgrade/overwrite status.
    sources_cli.route(_args(folder, "S-0001", language="en"), "en")
    assert registry.get(folder, "S-0001")["metadata_status"] == "matched"


def test_set_language_only_does_not_flip_unresolved(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    # S-0003 is unresolved with pre-existing (garbled) title+authors; a
    # language-only edit must not claim author identification.
    sources_cli.route(_args(folder, "S-0003", language="uk"), "en")
    rec = registry.get(folder, "S-0003")
    assert rec["language"] == "uk"
    assert rec["metadata_status"] == "unresolved"


def test_unresolve_reverts_status_and_strips_attestation(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    # First make S-0002 author_provided, then revert it.
    sources_cli.route(_args(folder, "S-0002", title="T", authors=["Smith, J."]), "en")
    assert registry.get(folder, "S-0002")["metadata_status"] == "author_provided"
    env, code = sources_cli.route(_args(folder, "S-0002", unresolve=True), "en")
    assert code == 0 and env["status"] == "ok"
    rec = registry.get(folder, "S-0002")
    assert rec["metadata_status"] == "unresolved"
    assert all(s.get("resource") != "author" for s in rec.get("metadata_sources", []))


def test_clear_authors_empties_list(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    env, code = sources_cli.route(_args(folder, "S-0003", unresolve=True, clear_authors=True), "en")
    assert code == 0
    rec = registry.get(folder, "S-0003")
    assert rec["authors"] == [] and rec["metadata_status"] == "unresolved"


def test_set_empty_patch_refused(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    with pytest.raises(InvalidInputError):
        sources_cli.route(_args(folder, "S-0001"), "en")


def test_set_unknown_source_refused(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    with pytest.raises(InvalidInputError):
        sources_cli.route(_args(folder, "S-9999", language="en"), "en")


def test_set_author_without_family_refused(tmp_path: Path) -> None:
    folder = _object(tmp_path)
    with pytest.raises(InvalidInputError):
        sources_cli.route(_args(folder, "S-0002", title="T", authors=[", Given"]), "en")
