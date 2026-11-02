"""Typical-errors profile and check (integrity.md; M3-13, FR-51).

The author chooses typical-error categories once; ``check_text`` reports findings
with proposed fixes — higher severity for chosen categories. Deterministic where
possible (listed calques, voice-mixing markers); semantic categories are left to
a reviewer subagent. The harness NEVER introduces an error into any version or
export (T56): this module only reports, never edits.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_CATALOG = Path(__file__).resolve().parents[3] / "rulepacks" / "core" / "errors-catalog.yaml"


def load_catalog(path: Path | None = None) -> dict[str, Any]:
    return yaml.safe_load((path or _CATALOG).read_text(encoding="utf-8"))


def _category(catalog: dict[str, Any], cid: str) -> dict[str, Any]:
    for c in catalog.get("categories", []):
        if c["id"] == cid:
            return c
    return {}


def _finding(chosen: bool, reason: str, fix: str, observed: str) -> dict[str, Any]:
    return {
        "check_id": "integrity.chosen_error" if chosen else "integrity.error",
        "severity": "major" if chosen else "minor",
        "reason": reason,
        "location": {},
        "observed": observed,
        "proposed_action": fix,
    }


def _calque_findings(text: str, catalog: dict[str, Any], chosen: set[str]) -> list[dict[str, Any]]:
    cat = _category(catalog, "calque_bureaucratese")
    is_chosen = "calque_bureaucratese" in chosen
    low = text.casefold()
    out: list[dict[str, Any]] = []
    for pair in cat.get("calques", []):
        bad, good = pair["bad"], pair["good"]
        if bad.casefold() in low:
            out.append(
                _finding(
                    is_chosen,
                    reason=f"calque/bureaucratese: {bad!r} (prefer {good!r})",
                    fix=f"Replace {bad!r} with {good!r}.",
                    observed=bad,
                )
            )
    return out


def _voice_findings(
    text: str, catalog: dict[str, Any], chosen: set[str], lang: str
) -> list[dict[str, Any]]:
    markers = catalog.get("voice_markers", {})
    low = text.casefold()
    present = {
        voice: sum(low.count(m.casefold()) for m in by_lang.get(lang, []))
        for voice, by_lang in markers.items()
    }
    used = [v for v, n in present.items() if n > 0]
    if len(used) < 2:
        return []
    is_chosen = "voice_person" in chosen
    return [
        _finding(
            is_chosen,
            reason=f"voice/person mixing: {', '.join(sorted(used))} in one text",
            fix="Keep one voice (I / we / impersonal) consistent with the style profile.",
            observed=",".join(sorted(used)),
        )
    ]


def check_text(
    text: str,
    *,
    chosen: set[str] | None = None,
    catalog: dict[str, Any] | None = None,
    lang: str = "uk",
) -> list[dict[str, Any]]:
    """Deterministic typical-error findings for ``text`` (never edits it)."""
    catalog = catalog or load_catalog()
    chosen = chosen or set()
    findings = _calque_findings(text, catalog, chosen)
    findings += _voice_findings(text, catalog, chosen, lang)
    return findings


# --- Errors profile (_author/errors-profile.yaml) ---------------------------


def profile_path(author_root: Path) -> Path:
    return author_root / "errors-profile.yaml"


def load_profile(author_root: Path) -> dict[str, Any]:
    p = profile_path(author_root)
    if not p.is_file():
        return {"chosen": [], "voice": "impersonal", "version": 1}
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def chosen_ids(profile: dict[str, Any]) -> set[str]:
    return {c["category_id"] for c in profile.get("chosen", []) if "category_id" in c}


def choose(author_root: Path, categories: list[str], voice: str | None = None) -> dict[str, Any]:
    """Set the author's chosen error categories (and voice). Validates ids."""
    catalog = load_catalog()
    known = {c["id"] for c in catalog.get("categories", [])}
    unknown = [c for c in categories if c not in known]
    if unknown:
        raise ValueError(f"unknown error categories: {unknown}")
    profile = load_profile(author_root)
    profile["chosen"] = [{"category_id": c} for c in categories]
    if voice:
        profile["voice"] = voice
    profile["version"] = int(profile.get("version", 0)) + 1
    author_root.mkdir(parents=True, exist_ok=True)
    profile_path(author_root).write_text(
        yaml.safe_dump(profile, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    return profile
