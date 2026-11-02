"""AI-use record and draft statement (M3-11, integrity.md, FR-32/FR-53).

Built only from data (invariant 2): the model-call log (``.rh/model-calls.jsonl``)
and paragraph provenance (``<unit>/provenance.json``). Never from the agent's
own description of what it did. The statement is a *draft* in the manuscript
language — what to submit is the author's decision (FR-16).

No code path here removes or hides AI-use traces (invariant 3). A request to make
AI output evade detection is not applied; it is reported as a finding (N4).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from research_harness.core.hashing import file_hash
from research_harness.models.calls import calls_path
from research_harness.provenance import paragraphs as prov
from research_harness.schemas import validate
from research_harness.structure import ops

# Role -> the stage of work it runs in (documented mapping; roles.yaml has only
# tiers). Used to describe AI use honestly; unknown roles keep their own name.
_ROLE_STAGE = {
    "researcher": "research",
    "analyst": "analysis",
    "writer": "drafting",
    "summarizer": "summarization",
    "triage": "triage",
    "classifier": "classification",
    "orchestrator": "orchestration",
    "unit_critic": "review",
    "chapter_critic": "review",
    "integration_critic": "review",
}

# Requests to conceal AI authorship (N4) — deterministic, uk + en. Matching is
# on casefolded text; these are never acted on, only flagged.
_CONCEAL_PATTERNS = (
    r"evade\s+(ai\s+)?detect",
    r"bypass\s+(ai\s+)?detect",
    r"(ai|content)\s+detector",
    r"undetectab",
    r"humaniz\w*\s+(the\s+)?(ai|text)",
    r"not\s+recogniz\w*\s+as\s+ai",
    r"обі[йг]ти\s+детектор",
    r"детектор\w*\s+шi|детектор\w*\s+ai",
    r"не\s+розпізна\w*\s+(як\s+)?(шi|ai)",
    r"прихова\w*\s+(використання\s+)?(шi|ai)",
)
_CONCEAL_RE = re.compile("|".join(_CONCEAL_PATTERNS), re.IGNORECASE)


def _rh_object_id(root: Path) -> str:
    obj = root / "object.json"
    if obj.is_file():
        try:
            return json.loads(obj.read_text(encoding="utf-8")).get("object_id", "unknown")
        except json.JSONDecodeError:
            pass
    return "unknown"


def read_calls(root: Path) -> list[dict[str, Any]]:
    path = calls_path(root)
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def provenance_shares(root: Path) -> dict[str, int]:
    """Count paragraphs by origin across every unit (FR-53)."""
    shares = {o: 0 for o in prov.ORIGINS}
    for uid in ops.current_folders(root):
        for para in prov.load_map(root, uid).values():
            origin = para.get("origin", "author")
            shares[origin] = shares.get(origin, 0) + 1
    return shares


def _entries(calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One entry per (role, model_id, tier, purpose) seen in successful calls."""
    groups: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for c in calls:
        if c.get("status") != "ok":
            continue
        role = c.get("role", "unknown")
        model_id = c.get("model_id", "unknown")
        tier = c.get("tier_required", "unknown")
        purpose = c.get("purpose", "unknown")
        key = (role, model_id, tier, purpose)
        at = c.get("at", "")
        g = groups.get(key)
        if g is None:
            groups[key] = {
                "stage": _ROLE_STAGE.get(role, role),
                "role": role,
                "model_id": model_id,
                "model_tier": tier,
                "purpose": purpose,
                "units": [],
                "at": at,
            }
        elif at and at < groups[key]["at"]:
            groups[key]["at"] = at
    return [groups[k] for k in sorted(groups)]


def build_record(root: Path) -> dict[str, Any]:
    calls = read_calls(root)
    shares = provenance_shares(root)
    generated_from: list[dict[str, str]] = []
    cp = calls_path(root)
    if cp.is_file():
        generated_from.append({"ref": "model-calls", "sha256": file_hash(cp)})
    for uid in ops.current_folders(root):
        pp = prov.provenance_path(root, uid)
        if pp.is_file():
            generated_from.append({"ref": f"provenance:{uid}", "sha256": file_hash(pp)})
    record = {
        "schema_version": "0.2",
        "object_id": _rh_object_id(root),
        "entries": _entries(calls),
        "provenance_shares": {o: shares.get(o, 0) for o in prov.ORIGINS},
        "generated_from": generated_from,
    }
    errors = validate("ai-use", record)
    if errors:
        raise ValueError(f"invalid ai-use record: {errors}")
    return record


def record_path(root: Path) -> Path:
    return root / "integrity" / "ai-use.json"


def write_record(root: Path, record: dict[str, Any]) -> Path:
    path = record_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def load_record(root: Path) -> dict[str, Any] | None:
    path = record_path(root)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def ai_use_present(root: Path) -> bool:
    return record_path(root).is_file()


def missing_finding(root: Path) -> dict[str, Any] | None:
    """``integrity.ai_use_missing`` — blocker for verified export (T34)."""
    if ai_use_present(root):
        return None
    return {
        "check_id": "integrity.ai_use_missing",
        "severity": "blocker",
        "reason": "no AI-use record; run `rh ai-use show` before a verified export",
        "location": {},
        "proposed_action": "Generate the AI-use record (rh ai-use show).",
    }


def _style_texts(root: Path) -> list[tuple[str, str]]:
    """(label, text) pairs where a concealment instruction could hide: the style
    profiles the author keeps under ``_author/style/``."""
    out: list[tuple[str, str]] = []
    style_dir = root.parent.parent / "_author" / "style"
    if style_dir.is_dir():
        for prof in style_dir.rglob("profile.yaml"):
            out.append((str(prof), prof.read_text(encoding="utf-8")))
    return out


def scan_concealment(text: str) -> list[str]:
    """Casefolded patterns matched in ``text`` (empty = none). Never acts on them."""
    return sorted({m.group(0) for m in _CONCEAL_RE.finditer(text)})


def concealment_findings(root: Path, extra: list[tuple[str, str]] | None = None) -> list[dict]:
    """``integrity.ai_concealment_request`` (major, N4) for any style text asking
    to hide AI authorship. ``extra`` lets callers add imported text to scan."""
    findings: list[dict[str, Any]] = []
    for label, text in [*_style_texts(root), *(extra or [])]:
        hits = scan_concealment(text)
        if hits:
            findings.append(
                {
                    "check_id": "integrity.ai_concealment_request",
                    "severity": "major",
                    "reason": f"request to conceal AI use, not applied: {', '.join(hits)}",
                    "location": {"path": label},
                    "observed": hits,
                    "proposed_action": "Remove the concealment instruction; AI use is not hidden.",
                }
            )
    return findings


def _is_thesis(root: Path) -> bool:
    stack = root / "profiles" / "resolved-stack.json"
    if not stack.is_file():
        return False
    try:
        rules = json.loads(stack.read_text(encoding="utf-8")).get("rules", [])
    except json.JSONDecodeError:
        return False
    return any(
        r.get("key") == "process.ai_statement_required" and r.get("pack") == "ua-mon-phd"
        for r in rules
    )


def build_statement(root: Path, lang: str) -> str:
    """Draft AI-use statement from the record, in the manuscript language."""
    record = build_record(root)
    shares = record["provenance_shares"]
    total = sum(shares.values())
    stages = sorted({e["stage"] for e in record["entries"]})
    purposes = sorted({e["purpose"] for e in record["entries"] if e["purpose"] != "unknown"})
    thesis = _is_thesis(root)
    if lang == "en":
        return _statement_en(shares, total, stages, purposes, thesis)
    return _statement_uk(shares, total, stages, purposes, thesis)


def _pct(n: int, total: int) -> str:
    return f"{(100 * n / total):.0f}%" if total else "0%"


def _statement_uk(shares, total, stages, purposes, thesis) -> str:
    kind = "дисертації" if thesis else "статті"
    stage_line = ", ".join(stages) if stages else "—"
    purpose_line = "; ".join(purposes) if purposes else "—"
    return (
        "# Заява про використання ШІ (чернетка)\n\n"
        f"Під час підготовки цього тексту {kind} використано інструменти ШІ на етапах: "
        f"{stage_line}. Призначення: {purpose_line}.\n\n"
        "Частка абзаців за походженням:\n"
        f"- автор: {shares['author']} ({_pct(shares['author'], total)});\n"
        f"- за участю ШІ, відредаговано автором: {shares['agent_edited_by_author']} "
        f"({_pct(shares['agent_edited_by_author'], total)});\n"
        f"- згенеровано ШІ: {shares['agent']} ({_pct(shares['agent'], total)}).\n\n"
        "Остаточне рішення щодо змісту та формулювань належить автору. "
        "Це чернетка, згенерована з даних провенансу; автор затверджує текст перед поданням.\n"
    )


def _statement_en(shares, total, stages, purposes, thesis) -> str:
    kind = "thesis" if thesis else "article"
    stage_line = ", ".join(stages) if stages else "—"
    purpose_line = "; ".join(purposes) if purposes else "—"
    return (
        "# AI-use statement (draft)\n\n"
        f"In preparing this {kind}, AI tools were used at the stages: {stage_line}. "
        f"Purposes: {purpose_line}.\n\n"
        "Share of paragraphs by origin:\n"
        f"- author: {shares['author']} ({_pct(shares['author'], total)});\n"
        f"- AI-assisted, edited by the author: {shares['agent_edited_by_author']} "
        f"({_pct(shares['agent_edited_by_author'], total)});\n"
        f"- AI-generated: {shares['agent']} ({_pct(shares['agent'], total)}).\n\n"
        "All content decisions are the author's. This is a draft generated from "
        "provenance data; the author confirms the wording before submission.\n"
    )


def statement_path(root: Path, lang: str) -> Path:
    return root / "integrity" / f"ai-statement.{lang}.md"
