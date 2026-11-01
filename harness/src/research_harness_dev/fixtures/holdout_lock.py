"""Build ``holdout.lock.json`` for a holdout package (05-eval-base §5.2, §9).

The holdout content (sources, manuscript, reference annotation, cases) is the
author's and never enters the repository (H1, H8). Only this lock file does:
case IDs, a SHA-256 of each file, and the creation date. The lock lets the PR
check (T41, M3) block any file whose hash is listed from ever being committed,
without the repo — or any agent — holding the content.

The author runs this **himself** on the decrypted archive in a scratch
directory outside the repo, e.g.::

    rh-dev fixtures holdout-lock --dir ~/rh-holdout-tmp/F4-H

It reads only the directory the author points at; it refuses a directory inside
the repository, so holdout content cannot be hashed in place where it might be
staged. No agent runs this against holdout content.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

# Entries never hashed/listed: VCS metadata and any previously written lock.
_SKIP_NAMES = {".git", ".DS_Store", "holdout.lock.json"}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _inside_repo(directory: Path) -> bool:
    """True if ``directory`` resolves to a path tracked by a git work tree."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=directory,
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
    root = Path(result.stdout.strip()).resolve()
    here = directory.resolve()
    return root == here or root in here.parents


def _iter_files(directory: Path) -> list[Path]:
    out: list[Path] = []
    for p in sorted(directory.rglob("*")):
        if not p.is_file():
            continue
        if any(part in _SKIP_NAMES for part in p.relative_to(directory).parts):
            continue
        out.append(p)
    return out


def _case_ids(directory: Path) -> list[str]:
    """Collect the ``id`` of every eval case YAML under ``cases/``."""
    ids: list[str] = []
    cases_dir = directory / "cases"
    if not cases_dir.is_dir():
        return ids
    for yml in sorted(cases_dir.rglob("*.yaml")):
        try:
            doc = yaml.safe_load(yml.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            continue
        cid = doc.get("id")
        if isinstance(cid, str):
            ids.append(cid)
    return sorted(set(ids))


def build_lock(
    directory: Path,
    *,
    fixture: str | None = None,
    created: str | None = None,
) -> dict[str, Any]:
    """Return the lock dict for the holdout package rooted at ``directory``.

    Raises ``ValueError`` if ``directory`` is missing, empty, or inside the
    repository (H1: holdout content must never live in the repo).
    """
    directory = directory.resolve()
    if not directory.is_dir():
        raise ValueError(f"not a directory: {directory}")
    if _inside_repo(directory):
        raise ValueError(
            f"{directory} is inside a git repo; decrypt the holdout archive to a "
            "scratch dir OUTSIDE the repository first (H1)."
        )
    files = _iter_files(directory)
    if not files:
        raise ValueError(f"no files found under {directory}")
    return {
        "schema_version": "0.2",
        "fixture": fixture or directory.name,
        "created": created or _dt.date.today().isoformat(),
        "case_ids": _case_ids(directory),
        "files": [
            {"path": p.relative_to(directory).as_posix(), "sha256": _sha256(p)} for p in files
        ],
    }


def main(argv: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="rh-dev fixtures holdout-lock")
    parser.add_argument(
        "--dir",
        required=True,
        help="Decrypted holdout package dir, OUTSIDE the repo (H1).",
    )
    parser.add_argument(
        "--out",
        help="Write the lock here (default: stdout). Commit it as "
        "harness/evals/holdout.lock.json via a PR.",
    )
    parser.add_argument("--fixture", help="Fixture id (default: the dir name).")
    args = parser.parse_args(argv)

    try:
        lock = build_lock(Path(args.dir).expanduser(), fixture=args.fixture)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    text = json.dumps(lock, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    if args.out:
        out = Path(args.out).expanduser()
        if "holdout" in out.resolve().as_posix().split("/")[:-1]:
            # The lock is the one artifact that MUST be outside holdout/: it is
            # the file that goes into the repo (05-eval-base §5.2).
            print("error: do not write the lock under a holdout/ path", file=sys.stderr)
            return 2
        out.write_text(text, encoding="utf-8")
        print(f"wrote {out} ({len(lock['files'])} files, {len(lock['case_ids'])} cases)")
    else:
        print(text, end="")
    return 0
