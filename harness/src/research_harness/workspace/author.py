"""Author level ``_author/`` with a versioned, immutable change log (02 §3.2)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from research_harness.core.clock import default_clock
from research_harness.core.errors import InvalidInputError
from research_harness.core.hashing import file_hash
from research_harness.state.snapshot import atomic_write_bytes

if TYPE_CHECKING:
    from research_harness.workspace.workspace import Workspace

HUMAN = {"kind": "human", "name": "rh", "version": "0.1.0"}

DEFAULT_PROFILE: dict[str, Any] = {
    "schema_version": "0.2",
    "name": "unknown",
    "orcid": "unknown",
    "affiliations": [],
    "languages": ["uk"],
    "ui_language": "uk",
    "default_autonomy": "gates",
    "voice": "impersonal",
}


def author_dir(ws: Workspace) -> Path:
    return ws.root / "_author"


def profile_path(ws: Workspace) -> Path:
    return author_dir(ws) / "profile.yaml"


def versions_path(ws: Workspace) -> Path:
    return author_dir(ws) / "versions.jsonl"


def _write_yaml(path: Path, obj: Any) -> None:
    atomic_write_bytes(
        path, yaml.safe_dump(obj, allow_unicode=True, sort_keys=True).encode("utf-8")
    )


def init_author(ws: Workspace) -> None:
    d = author_dir(ws)
    (d / "corpus").mkdir(parents=True, exist_ok=True)
    _write_yaml(profile_path(ws), DEFAULT_PROFILE)
    (d / "publications.bib").write_text("", encoding="utf-8")
    atomic_write_bytes(d / "corpus" / "index.json", b'{"files": []}\n')
    versions_path(ws).write_text("", encoding="utf-8")
    for rel in ("profile.yaml", "publications.bib", "corpus/index.json"):
        _append_version(ws, rel)


def read_profile(ws: Workspace) -> dict[str, Any]:
    return yaml.safe_load(profile_path(ws).read_text(encoding="utf-8")) or {}


def current_version(ws: Workspace, rel: str) -> int:
    vp = versions_path(ws)
    if not vp.exists():
        return 0
    n = 0
    for line in vp.read_text(encoding="utf-8").splitlines():
        if line.strip() and json.loads(line).get("file") == rel:
            n += 1
    return n


def _append_version(ws: Workspace, rel: str) -> int:
    n = current_version(ws, rel) + 1
    stem = Path(rel).stem
    entry = {
        "id": f"author:{stem}@v{n}",
        "file": rel,
        "version": n,
        "sha256": file_hash(author_dir(ws) / rel),
        "created_at": default_clock().now_rfc3339(),
        "producer": HUMAN,
    }
    with open(versions_path(ws), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
    return n


def set_field(ws: Workspace, key: str, value: Any) -> int:
    profile = read_profile(ws)
    if key not in DEFAULT_PROFILE and key not in ("name_latin", "contact_email"):
        raise InvalidInputError("error.author_unknown_field")
    profile[key] = value
    _write_yaml(profile_path(ws), profile)
    return _append_version(ws, "profile.yaml")


def current_pin(ws: Workspace) -> dict[str, Any]:
    """The pin an object records at creation (02 §3.2): version ref + hash."""
    n = current_version(ws, "profile.yaml")
    return {"profile": {"ref": f"author:profile@v{n}", "sha256": file_hash(profile_path(ws))}}
