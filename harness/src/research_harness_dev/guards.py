"""Static guards for ``rh-dev check`` (M1-02).

- Import guard (H5, NFR-07, T15): ``research_harness`` must not import an LLM
  SDK, a rejected PDF/LLM package, a host adapter, or ``research_harness_dev``.
- Envelope-literal guard (02 §1.6): no user-facing string literal passed as
  ``message=`` / ``why=`` or assigned to ``.message`` / ``.why``.
- i18n catalog guard: ``uk.yaml`` and ``en.yaml`` define the same keys.
- Lockfile guard: forbidden dependencies must not appear in ``uv.lock``.
- Adoption guard (H4, FR-24, T24): every third-party file has a valid record.
"""

from __future__ import annotations

import ast
import hashlib
import json
import tomllib
from pathlib import Path

# --- Import guard -----------------------------------------------------------

FORBIDDEN_IMPORTS_EXACT = frozenset(
    {"anthropic", "openai", "litellm", "fitz", "pymupdf", "paperqa", "research_harness_dev"}
)
FORBIDDEN_IMPORTS_PREFIX = ("langchain", "google.generativeai")


def _module_forbidden(module: str) -> bool:
    top = module.split(".")[0]
    if module in FORBIDDEN_IMPORTS_EXACT or top in FORBIDDEN_IMPORTS_EXACT:
        return True
    return any(module == p or module.startswith(p + ".") for p in FORBIDDEN_IMPORTS_PREFIX)


def scan_forbidden_imports(package_root: Path) -> list[str]:
    """Return ``file:line module`` violations under ``package_root``."""
    violations: list[str] = []
    for py in sorted(package_root.rglob("*.py")):
        tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if _module_forbidden(alias.name):
                        violations.append(f"{py}:{node.lineno} import {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                if _module_forbidden(node.module):
                    violations.append(f"{py}:{node.lineno} from {node.module}")
    return violations


# --- Envelope-literal guard -------------------------------------------------

_USER_FACING = {"message", "why"}


def scan_envelope_literals(package_root: Path) -> list[str]:
    """Flag user-facing string literals used instead of an i18n key."""
    violations: list[str] = []
    for py in sorted(package_root.rglob("*.py")):
        tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                for kw in node.keywords:
                    if (
                        kw.arg in _USER_FACING
                        and isinstance(kw.value, ast.Constant)
                        and isinstance(kw.value.value, str)
                    ):
                        violations.append(f"{py}:{kw.value.lineno} {kw.arg}=<literal>")
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if (
                        isinstance(target, ast.Attribute)
                        and target.attr in _USER_FACING
                        and isinstance(node.value, ast.Constant)
                        and isinstance(node.value.value, str)
                    ):
                        violations.append(f"{py}:{node.lineno} .{target.attr}=<literal>")
    return violations


# --- i18n catalog guard -----------------------------------------------------


def check_i18n_catalogs(i18n_dir: Path, langs: tuple[str, ...] = ("uk", "en")) -> list[str]:
    """Return messages for keys present in one catalog but missing in another."""
    import yaml

    catalogs: dict[str, set[str]] = {}
    for lang in langs:
        loaded = yaml.safe_load((i18n_dir / f"{lang}.yaml").read_text(encoding="utf-8")) or {}
        catalogs[lang] = set(loaded.keys())
    all_keys: set[str] = set().union(*catalogs.values()) if catalogs else set()
    problems: list[str] = []
    for key in sorted(all_keys):
        missing = [lang for lang in langs if key not in catalogs[lang]]
        if missing:
            problems.append(f"key {key!r} missing from: {', '.join(missing)}")
    return problems


# --- Lockfile guard ---------------------------------------------------------

FORBIDDEN_DEPS = frozenset({"pymupdf", "paper-qa-pymupdf", "paper-qa", "paperqa"})


def _normalize(name: str) -> str:
    return name.lower().replace("_", "-")


def scan_lockfile(lockfile: Path) -> list[str]:
    """Return forbidden dependency names found in ``uv.lock``."""
    if not lockfile.exists():
        return []
    data = tomllib.loads(lockfile.read_text(encoding="utf-8"))
    hits: list[str] = []
    for pkg in data.get("package", []):
        name = pkg.get("name", "")
        if _normalize(name) in FORBIDDEN_DEPS:
            hits.append(name)
    return hits


# --- Adoption guard ---------------------------------------------------------

ALLOWED_LICENSES = frozenset(
    {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "PSF-2.0", "ISC"}
)
_HEX40 = frozenset("0123456789abcdef")


def _sha256_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_adoptions(repo_root: Path) -> list[str]:
    """Validate adoption records (02 §13, 06 §2.3 subset for M1)."""
    problems: list[str] = []
    harness = repo_root / "harness"
    manifest_path = harness / "third_party" / "manifest.json"
    if not manifest_path.exists():
        return [f"missing {manifest_path}"]

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = manifest.get("adoptions", [])
    notices = (repo_root / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")

    accounted: set[Path] = {manifest_path}
    for rec in records:
        rid = rec.get("id", "<no-id>")
        commit = rec.get("commit", "")
        if len(commit) != 40 or any(c not in _HEX40 for c in commit.lower()):
            problems.append(f"{rid}: commit is not a 40-hex SHA")
        if rec.get("license") not in ALLOWED_LICENSES:
            problems.append(f"{rid}: license {rec.get('license')!r} not in allowed list")

        original = rec.get("original_copy")
        if original:
            opath = harness / original
            accounted.add(opath)
            if not opath.exists():
                problems.append(f"{rid}: original_copy missing: {original}")
            elif _sha256_bytes(opath) != rec.get("original_sha256"):
                problems.append(f"{rid}: original_sha256 mismatch for {original}")

        license_file = rec.get("license_file")
        if license_file:
            accounted.add(harness / license_file)

        dest = rec.get("destination")
        if rec.get("mode") != "idea":
            if not dest:
                problems.append(f"{rid}: destination required for mode {rec.get('mode')!r}")
            else:
                dpath = harness / dest
                if not dpath.exists():
                    problems.append(f"{rid}: destination missing: {dest}")
                else:
                    text = dpath.read_text(encoding="utf-8")
                    if "Adapted from" not in text and rec.get("mode") != "copy":
                        problems.append(f"{rid}: destination lacks an 'Adapted from' header")
                    if _sha256_bytes(dpath) != rec.get("adapted_sha256"):
                        problems.append(f"{rid}: adapted_sha256 mismatch for {dest}")

        for test_id in rec.get("acceptance_tests", []):
            if ".py" in test_id:
                node_path = test_id.split("::", 1)[0]
                if not (harness / node_path).exists():
                    problems.append(f"{rid}: acceptance test file missing: {node_path}")
        if rid not in notices:
            problems.append(f"{rid}: no entry in THIRD_PARTY_NOTICES.md")

    # Every file under third_party/ must belong to a record (LICENSE files ok).
    tp_root = harness / "third_party"
    for f in sorted(tp_root.rglob("*")):
        if f.is_file() and f not in accounted:
            problems.append(
                f"unaccounted third-party file (no adoption record): {f.relative_to(harness)}"
            )
    return problems
