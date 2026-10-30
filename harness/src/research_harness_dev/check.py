"""`rh-dev check` — standing repository checks.

Runs, in order (01 §4 of card M1-01):
  1. ruff check
  2. ruff format --check
  3. pytest -q
  4. forbidden-path scan — any tracked or staged file matching a pattern in
     01 §5 fails the check and the offending paths are listed.

Later cards append steps to this runner (e.g. the import / dependency guards in
M1-02, the full PR check with T41 in M3).
"""

from __future__ import annotations

import re
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

from research_harness_dev.guards import (
    check_i18n_catalogs,
    scan_envelope_literals,
    scan_forbidden_imports,
    scan_lockfile,
    validate_adoptions,
)

# Patterns that must never be tracked by git (01 §5). A pattern without a slash
# is matched against each path's basename (gitignore semantics); a pattern with
# a slash or `**` is matched against the full POSIX path relative to the repo
# root. The hash-based part (files whose hash is in holdout.lock.json, datasets
# with storage: no_copy) is enforced by the full PR check in M3 (T41); it is a
# no-op here while those files do not exist.
FORBIDDEN_PATTERNS: tuple[str, ...] = (
    "**/holdout/**",
    "Projects/**/sources/inbox/**",
    "Projects/**/sources/fulltext/**",
    "Projects/**/sources/pagetext/**",
    "Projects/**/materials/private/**",
    ".env",
    "*.local.yaml",
    "**/secrets/**",
    "source-policy.local.yaml",
    "Projects/**/.rh/staging/**",
    "Projects/**/.rh/quarantine/**",
    "Projects/**/.rh/lock",
    "Projects/**/work/**",
    "Projects/**/.rh/library.sqlite",
    "Projects/**/analysis/data/**",
)


def _glob_to_regex(pattern: str) -> re.Pattern[str]:
    """Translate a limited glob (``**``, ``*``, ``?``) to an anchored regex."""
    out: list[str] = ["^"]
    i, n = 0, len(pattern)
    while i < n:
        if pattern.startswith("**/", i):
            out.append(r"(?:.*/)?")
            i += 3
        elif pattern.startswith("/**", i):
            out.append(r"(?:/.*)?")
            i += 3
        elif pattern[i] == "*":
            out.append(r"[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append(r"[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    out.append("$")
    return re.compile("".join(out))


_COMPILED = [(p, "/" not in p, _glob_to_regex(p)) for p in FORBIDDEN_PATTERNS]


def git_root(start: Path | None = None) -> Path:
    """Return the git top-level directory containing ``start`` (default cwd)."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=start or Path.cwd(),
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(result.stdout.strip())


def tracked_paths(repo_root: Path) -> list[str]:
    """POSIX paths of every file git tracks or has staged in ``repo_root``."""
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def forbidden_hits(paths: Iterable[str]) -> list[str]:
    """Return the subset of ``paths`` that match a forbidden pattern."""
    hits: list[str] = []
    for path in paths:
        basename = path.rsplit("/", 1)[-1]
        for _pattern, basename_only, regex in _COMPILED:
            target = basename if basename_only else path
            if regex.match(target):
                hits.append(path)
                break
    return hits


def scan_forbidden_paths(repo_root: Path) -> list[str]:
    """Scan tracked/staged files; return forbidden paths (empty = clean)."""
    return forbidden_hits(tracked_paths(repo_root))


def _run(label: str, cmd: list[str], cwd: Path) -> bool:
    print(f"==> {label}: {' '.join(cmd)}", flush=True)
    completed = subprocess.run(cmd, cwd=cwd)
    ok = completed.returncode == 0
    print(f"    {'PASS' if ok else 'FAIL'}: {label}")
    return ok


def check_main(argv: list[str] | None = None) -> int:
    cwd = Path.cwd()
    repo = git_root(cwd)
    failures: list[str] = []

    steps: list[tuple[str, list[str]]] = [
        ("ruff check", [sys.executable, "-m", "ruff", "check", "."]),
        ("ruff format --check", [sys.executable, "-m", "ruff", "format", "--check", "."]),
        ("pytest", [sys.executable, "-m", "pytest", "-q"]),
    ]
    for label, cmd in steps:
        if not _run(label, cmd, cwd):
            failures.append(label)

    def _static(label: str, section: str, problems: list[str]) -> None:
        print(f"==> {label} ({section})", flush=True)
        if problems:
            failures.append(label)
            print(f"    FAIL: {label}")
            for problem in problems:
                print(f"      {problem}")
        else:
            print(f"    PASS: {label}")

    _static("forbidden-path scan", "01 §5", scan_forbidden_paths(repo))

    package_root = cwd / "src" / "research_harness"
    _static("import guard", "H5, T15", scan_forbidden_imports(package_root))
    _static("envelope-literal guard", "02 §1.6", scan_envelope_literals(package_root))
    _static("i18n catalog guard", "02 §1.6", check_i18n_catalogs(package_root / "i18n"))
    _static("lockfile guard", "01 §3", scan_lockfile(cwd / "uv.lock"))
    _static("adoption records", "H4, T24", validate_adoptions(repo))

    if failures:
        print(f"\nrh-dev check: FAILED ({', '.join(failures)})")
        return 1
    print("\nrh-dev check: OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    """`rh-dev` dispatcher: ``check`` (default) and ``fixtures generate <name>``."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "fixtures":
        from research_harness_dev.fixtures.cli import main as fixtures_main

        return fixtures_main(args[1:])
    if args and args[0] == "host":
        from research_harness_dev.host import main as host_main

        return host_main(args[1:])
    if args and args[0] == "check":
        args = args[1:]
    return check_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
