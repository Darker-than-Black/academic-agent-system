"""Repository / PR safety check (integrity.md; M3-14, FR-16, NFR-06, NFR-11).

Blocks anything that must never enter git: files under ``**/holdout/**`` or whose
hash is in ``harness/evals/holdout.lock.json``, foreign full texts and private
material, secrets (API-key and private-key patterns), and local env/secret
files. Deterministic; found text is data, never instructions (H10). Shared by
``rh repo check`` and ``rh-dev check``; never reads a holdout file (H1).
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from collections.abc import Iterable
from pathlib import Path

# --- Forbidden paths (01 §5) ------------------------------------------------
# A pattern without a slash matches each path's basename (gitignore semantics);
# a pattern with a slash or ``**`` matches the full POSIX path from the repo root.
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


def _is_forbidden(path: str) -> bool:
    basename = path.rsplit("/", 1)[-1]
    for _pattern, basename_only, regex in _COMPILED:
        if regex.match(basename if basename_only else path):
            return True
    return False


def forbidden_hits(paths: Iterable[str]) -> list[str]:
    """Return the subset of ``paths`` that match a forbidden pattern."""
    return [p for p in paths if _is_forbidden(p)]


# --- Secrets ----------------------------------------------------------------
# Length quantifiers keep these patterns from matching their own source text.
SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("anthropic_key", re.compile(r"sk-ant-[A-Za-z0-9_-]{24,}")),
    ("openai_key", re.compile(r"sk-[A-Za-z0-9]{32,}")),
    ("openai_project_key", re.compile(r"sk-proj-[A-Za-z0-9_-]{24,}")),
    ("private_key_block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("bearer_token", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]{20,}=*")),
    (
        "generic_key_assignment",
        re.compile(r"(?i)[A-Z0-9_]*_KEY\s*[=:]\s*['\"]?[A-Za-z0-9/_+-]{16,}"),
    ),
    (
        "url_with_token",
        re.compile(r"https?://[^\s'\"]*[?&](?:api_?key|token|access_token)=[^\s'\"&]+"),
    ),
)

# Extensions that are safe to read as text; others are skipped (binary).
_TEXT_SUFFIXES = frozenset(
    {
        ".py",
        ".md",
        ".txt",
        ".yaml",
        ".yml",
        ".json",
        ".jsonl",
        ".toml",
        ".cfg",
        ".ini",
        ".env",
        ".sh",
        ".csv",
        ".tsv",
        ".html",
        ".xml",
        ".tex",
        "",
    }
)


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def secret_hits(repo_root: Path, paths: Iterable[str]) -> list[tuple[str, str]]:
    """Scan the content of text files for secret patterns.

    Returns ``(path, pattern_name)`` pairs. Forbidden paths (holdout included)
    are never read (H1)."""
    hits: list[tuple[str, str]] = []
    for rel in paths:
        if _is_forbidden(rel):
            continue
        p = repo_root / rel
        if p.suffix.lower() not in _TEXT_SUFFIXES or not p.is_file():
            continue
        text = _read_text(p)
        if text is None:
            continue
        for name, pattern in SECRET_PATTERNS:
            if pattern.search(text):
                hits.append((rel, name))
    return hits


# --- Holdout hashes ---------------------------------------------------------


def load_holdout_hashes(repo_root: Path) -> set[str]:
    """SHA-256 hashes listed in ``harness/evals/holdout.lock.json`` (if present)."""
    import json

    lock = repo_root / "harness" / "evals" / "holdout.lock.json"
    if not lock.is_file():
        return set()
    data = json.loads(lock.read_text(encoding="utf-8"))
    return {f["sha256"] for f in data.get("files", []) if "sha256" in f}


def holdout_hash_hits(repo_root: Path, paths: Iterable[str]) -> list[str]:
    """Tracked files whose content hash is a holdout hash (content copied out)."""
    hashes = load_holdout_hashes(repo_root)
    if not hashes:
        return []
    hits: list[str] = []
    for rel in paths:
        if _is_forbidden(rel):
            continue
        p = repo_root / rel
        if not p.is_file():
            continue
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        if digest in hashes:
            hits.append(rel)
    return hits


# --- Path collection --------------------------------------------------------


def git_root(start: Path | None = None) -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=start or Path.cwd(),
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(result.stdout.strip())


def tracked_paths(repo_root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"], cwd=repo_root, capture_output=True, text=True, check=True
    )
    return [line for line in result.stdout.splitlines() if line]


def staged_paths(repo_root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def scan_forbidden_paths(repo_root: Path) -> list[str]:
    """Forbidden tracked paths (empty = clean). Kept for ``rh-dev check``."""
    return forbidden_hits(tracked_paths(repo_root))


# --- Report + findings ------------------------------------------------------


def run(repo_root: Path, *, staged: bool = False) -> dict:
    """Run every repository check; return a plain report."""
    paths = staged_paths(repo_root) if staged else tracked_paths(repo_root)
    return {
        "scope": "staged" if staged else "tracked",
        "n_paths": len(paths),
        "forbidden_paths": forbidden_hits(paths),
        "holdout_hashes": holdout_hash_hits(repo_root, paths),
        "secrets": secret_hits(repo_root, paths),
    }


def findings_from(report: dict) -> list[dict]:
    """Blocker findings for each offending path (NFR-11, T41)."""
    findings: list[dict] = []
    for path in report["forbidden_paths"]:
        findings.append(
            _f("repo.forbidden_path", path, f"forbidden path must not be tracked: {path}")
        )
    for path in report["holdout_hashes"]:
        findings.append(_f("repo.holdout", path, f"content hash matches a holdout file: {path}"))
    for path, name in report["secrets"]:
        findings.append(_f("repo.secret", path, f"possible secret ({name}) in {path}"))
    return findings


def _f(check_id: str, path: str, reason: str) -> dict:
    return {
        "check_id": check_id,
        "severity": "blocker",
        "reason": reason,
        "location": {"path": path},
        "observed": path,
        "proposed_action": "Remove the file from the commit / PR before it leaves the harness.",
    }
