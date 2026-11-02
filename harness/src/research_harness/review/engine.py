"""Review engine selection and the Codex critic (M3-17, review.md, FR-58).

A critic from another model family (Codex) is OFF by default and gated three
ways, checked here:

* ``codex_critic.enabled`` in ``harness/config/review.yaml`` — off ⇒ a request
  for ``--engine codex`` is refused (the CLI exits 3 with an explanation);
* intake Q3b (external-API permission) — not an explicit ``yes`` ⇒
  ``blocked_by_permissions``, no call;
* the Codex binary / credentials — absent ⇒ ``unavailable``, with a fallback to
  the Claude critic in a fresh context, recorded in the request.

When enabled, permitted and available, the critic runs ``codex exec`` in
non-interactive mode (``--json``, read-only sandbox — verified against the
OpenAI Codex docs, developers.openai.com/codex/noninteractive, 2026-11-02, H12),
but only after the paid-budget guard allows the call (H9); nothing here enables a
paid API. The model id is logged (FR-55).
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import yaml

from research_harness.intake import answers as answers_mod

_CONFIG = Path(__file__).resolve().parents[3] / "config" / "review.yaml"

# Engine status values recorded on the review request (review.md data contract).
OK = "ok"
UNAVAILABLE = "unavailable"
BLOCKED = "blocked_by_permissions"
DISABLED = "disabled"


def load_config() -> dict[str, Any]:
    if not _CONFIG.is_file():
        return {}
    return yaml.safe_load(_CONFIG.read_text(encoding="utf-8")) or {}


def codex_enabled() -> bool:
    return bool(load_config().get("codex_critic", {}).get("enabled", False))


def codex_model() -> str:
    return str(load_config().get("codex_critic", {}).get("model", "")) or "unknown"


def codex_available() -> bool:
    """The Codex CLI is installed (credentials are checked by the CLI itself)."""
    return shutil.which("codex") is not None


def q3b_permits(root: Path) -> bool:
    """True only on an explicit ``yes`` to Q3b (external-model APIs permitted)."""
    entry = answers_mod.load(root).get("answers", {}).get("Q3b")
    value = entry.get("value") if isinstance(entry, dict) else None
    return value in (True, "yes")


def resolve_engine(root: Path, requested: str) -> dict[str, Any]:
    """Resolve the critic engine and its status for a review request.

    Returns ``{engine, engine_status, requested, reason}``; ``engine`` is the
    engine that will actually review (the Claude critic is the fallback)."""
    if requested != "codex":
        return {"engine": "claude", "engine_status": OK, "requested": requested, "reason": ""}

    if not codex_enabled():
        return {
            "engine": "codex",
            "engine_status": DISABLED,
            "requested": "codex",
            "reason": "codex_critic.enabled is false (harness/config/review.yaml)",
        }
    if not q3b_permits(root):
        return {
            "engine": "claude",
            "engine_status": BLOCKED,
            "requested": "codex",
            "reason": "intake Q3b does not permit external-model APIs for this object",
        }
    if not codex_available():
        return {
            "engine": "claude",
            "engine_status": UNAVAILABLE,
            "requested": "codex",
            "reason": "the Codex CLI was not found; falling back to the Claude critic",
        }
    return {"engine": "codex", "engine_status": OK, "requested": "codex", "reason": ""}


def build_argv(work_dir: Path, prompt: str) -> list[str]:
    """Non-interactive Codex invocation (verified 2026-11-02, H12): JSON output,
    read-only sandbox (the default), run in the context-pack directory."""
    return ["codex", "exec", "--json", "--cd", str(work_dir), prompt]
