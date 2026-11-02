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

import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

import yaml

from research_harness.intake import answers as answers_mod

_CONFIG = Path(__file__).resolve().parents[3] / "config" / "review.yaml"

_UNKNOWN = "unknown"

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


# --- live run (M3-17, P1-1) -------------------------------------------------


def _parse_codex_jsonl(stdout: str) -> dict[str, Any]:
    """Parse ``codex exec --json`` output (JSON Lines; format verified against
    learn.chatgpt.com/docs/non-interactive-mode, 2026-11-02, H12).

    Each line is an event keyed by ``type``. The critic's answer is the last
    ``item.completed`` whose ``item.type`` is ``agent_message`` (its ``text``);
    token counts are in the ``usage`` object of ``turn.completed``;
    ``turn.failed`` / ``error`` mark a failed run. Non-JSON lines are ignored
    (H10: output is data)."""
    agent_text: str | None = None
    usage: dict[str, Any] = {}
    failed = False
    error: Any = None
    for raw in stdout.splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(ev, dict):
            continue
        etype = ev.get("type")
        if etype == "item.completed":
            item = ev.get("item")
            if isinstance(item, dict) and item.get("type") == "agent_message":
                agent_text = item.get("text", agent_text)
        elif etype == "turn.completed":
            u = ev.get("usage")
            if isinstance(u, dict):
                usage = u
        elif etype in ("turn.failed", "error"):
            failed = True
            error = ev.get("error", ev)
    return {"agent_text": agent_text, "usage": usage, "failed": failed, "error": error}


def _map_results(agent_text: str | None) -> dict[str, Any]:
    """Map the critic's final message (a JSON object with ``findings`` and
    ``verdicts``) to our schemas, validating each item. Never invents data
    (H6): a missing or malformed message yields empty lists plus an error."""
    from research_harness.schemas import validate

    if not agent_text:
        return {"findings": [], "verdicts": [], "parse_error": "no agent_message in output"}
    try:
        payload = json.loads(agent_text)
    except json.JSONDecodeError as exc:
        return {"findings": [], "verdicts": [], "parse_error": f"agent message is not JSON: {exc}"}
    if not isinstance(payload, dict):
        return {"findings": [], "verdicts": [], "parse_error": "agent message is not a JSON object"}
    findings = payload.get("findings") or []
    verdicts = payload.get("verdicts") or []
    schema_errors: list[str] = []
    for v in verdicts:
        errs = validate("verdict", v)
        if errs:
            schema_errors.append(f"verdict: {errs[0]}")
    for f in findings:
        errs = validate("finding", f)
        if errs:
            schema_errors.append(f"finding: {errs[0]}")
    return {
        "findings": findings,
        "verdicts": verdicts,
        "parse_error": None,
        "schema_errors": schema_errors,
    }


def run_codex(
    root: Path,
    work_dir: Path,
    prompt: str,
    *,
    role: str = "unit_critic",
    host: str = "codex",
    timeout: float = 600.0,
) -> dict[str, Any]:
    """Run the Codex critic as a live subprocess and return its mapped result.

    The paid-budget guard runs FIRST (H9): a Codex call spends paid credits, so
    when ``paid_calls`` is not enabled with a recorded approval the guard refuses
    and no subprocess starts. On an allowed call it runs ``codex exec --json``,
    parses the JSONL, maps the final message to our finding/verdict schemas, and
    logs the model id and token usage (FR-55); that model-call log line is the
    stored record of the handoff. Persisting the verdicts against claims is the
    caller's step (``review.verdicts.submit`` with a review id)."""
    from research_harness.budget import controller as budget_mod
    from research_harness.models import calls as calls_mod
    from research_harness.models.config import tier_for_role

    model_id = codex_model()
    tier = tier_for_role(role)

    budget = budget_mod.load_budget(root)
    guard = budget_mod.check(budget, budget_mod.usage_from_calls(root), paid=True)
    if not guard["allowed"]:
        return {
            "status": "refused",
            "allowed": False,
            "findings": list(guard["findings"]),
            "verdicts": [],
            "model_id": model_id,
            "reason": "paid call not authorised; budget guard refused (H9)",
        }

    argv = build_argv(work_dir, prompt)
    start = time.monotonic()
    try:
        proc = subprocess.run(
            argv, cwd=str(work_dir), capture_output=True, text=True, timeout=timeout
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        duration = round(time.monotonic() - start, 3)
        calls_mod.log_call(
            root,
            host=host,
            role=role,
            tier_required=tier,
            model_id=model_id,
            purpose="codex_critic",
            duration_s=duration,
            status="failed",
        )
        return {
            "status": "failed",
            "allowed": True,
            "findings": [],
            "verdicts": [],
            "model_id": model_id,
            "reason": f"codex subprocess error: {exc}",
        }

    duration = round(time.monotonic() - start, 3)
    parsed = _parse_codex_jsonl(proc.stdout)
    call_ok = proc.returncode == 0 and not parsed["failed"]

    token_kwargs: dict[str, Any] = {}
    usage = parsed["usage"]
    if isinstance(usage.get("input_tokens"), int):
        token_kwargs["tokens_in"] = usage["input_tokens"]
    if isinstance(usage.get("output_tokens"), int):
        token_kwargs["tokens_out"] = usage["output_tokens"]
    call_rec = calls_mod.log_call(
        root,
        host=host,
        role=role,
        tier_required=tier,
        model_id=model_id,
        purpose="codex_critic",
        duration_s=duration,
        status="ok" if call_ok else "failed",
        **token_kwargs,
    )

    mapped = _map_results(parsed["agent_text"])
    if not call_ok:
        status = "failed"
    elif mapped["parse_error"] or mapped.get("schema_errors"):
        status = "unparsable"
    else:
        status = "ok"
    return {
        "status": status,
        "allowed": True,
        "findings": mapped["findings"],
        "verdicts": mapped["verdicts"],
        "model_id": model_id,
        "model_call_id": call_rec["id"],
        "usage": usage,
        "duration_s": duration,
        "parse_error": mapped["parse_error"],
        "schema_errors": mapped.get("schema_errors", []),
        "returncode": proc.returncode,
        "reason": "" if call_ok else f"codex run failed: {parsed['error']}",
    }
