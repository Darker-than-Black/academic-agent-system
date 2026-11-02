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

import subprocess
import sys
from pathlib import Path

# The repository / PR check now lives in the core package (integrity.repo, card
# M3-14) so both `rh repo check` and this gate run identical logic; the names
# below are re-exported for callers and tests that import them from here.
from research_harness.integrity.repo import (
    FORBIDDEN_PATTERNS,
    findings_from,
    forbidden_hits,
    git_root,
    scan_forbidden_paths,
    tracked_paths,
)
from research_harness.integrity.repo import run as repo_check
from research_harness_dev.guards import (
    check_i18n_catalogs,
    scan_envelope_literals,
    scan_forbidden_imports,
    scan_lockfile,
    scan_yaml_truthiness,
    validate_adoptions,
)

__all__ = [
    "FORBIDDEN_PATTERNS",
    "forbidden_hits",
    "git_root",
    "scan_forbidden_paths",
    "tracked_paths",
    "check_main",
    "main",
]


def _repo_problems(repo_root: Path) -> list[str]:
    """Forbidden paths, holdout-hash matches and secrets as gate problem lines."""
    report = repo_check(repo_root)
    return [f"{f['check_id']}: {f['location']['path']}" for f in findings_from(report)]


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

    _static("repo check (paths, holdout hashes, secrets)", "T41, NFR-11", _repo_problems(repo))

    package_root = cwd / "src" / "research_harness"
    _static("import guard", "H5, T15", scan_forbidden_imports(package_root))
    _static("envelope-literal guard", "02 §1.6", scan_envelope_literals(package_root))
    _static("i18n catalog guard", "02 §1.6", check_i18n_catalogs(package_root / "i18n"))
    _static(
        "yaml truthiness guard",
        "PH-2",
        scan_yaml_truthiness((cwd / "config", cwd / "intake", cwd / "rulepacks")),
    )
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
