"""Research protocol (``protocol/protocol-v<N>.yaml``): drafted, frozen at G1,
re-versioned for changes (02-lifecycle §4; FR-56).

Required fields and the default saturation rule come from the active study-kind
pack (``harness/rulepacks/<pack>/protocol.yaml``). A topic-only object gets a
discovery plan, not an invented protocol (H6). After G1, a material change to a
scope field keeps the frozen version and needs a fresh G2.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from research_harness.schemas import validate
from research_harness.sources.policy import load_policy
from research_harness.sources.policy import resources as policy_resources

_PROTO_RE = re.compile(r"^protocol-v(\d+)\.yaml$")

# study_kind -> rule-pack directory holding protocol.yaml.
_PACK_FOR = {"literature": "literature-narrative", "conceptual": "conceptual"}
_RULEPACKS = Path(__file__).resolve().parents[3] / "rulepacks"


def protocol_dir(root: Path) -> Path:
    d = root / "protocol"
    d.mkdir(parents=True, exist_ok=True)
    return d


def protocol_path(root: Path, version: int) -> Path:
    return root / "protocol" / f"protocol-v{version}.yaml"


def discovery_path(root: Path) -> Path:
    return root / "protocol" / "discovery-plan.yaml"


def summary_path(root: Path) -> Path:
    return root / "protocol" / "summary.md"


def study_kind(root: Path) -> str:
    obj = json.loads((root / "object.json").read_text(encoding="utf-8"))
    return obj.get("study_kind", "unknown")


def pack_config(kind: str) -> dict[str, Any] | None:
    pack = _PACK_FOR.get(kind)
    if pack is None:
        return None
    cfg = _RULEPACKS / pack / "protocol.yaml"
    if not cfg.is_file():
        return None
    return yaml.safe_load(cfg.read_text(encoding="utf-8"))


def latest_version(root: Path) -> int:
    d = root / "protocol"
    if not d.is_dir():
        return 0
    nums = [int(m.group(1)) for f in d.iterdir() if (m := _PROTO_RE.match(f.name))]
    return max(nums) if nums else 0


def load_version(root: Path, version: int) -> dict[str, Any]:
    return yaml.safe_load(protocol_path(root, version).read_text(encoding="utf-8"))


def load_latest(root: Path) -> dict[str, Any] | None:
    v = latest_version(root)
    return load_version(root, v) if v else None


def latest_frozen(root: Path) -> dict[str, Any] | None:
    for v in range(latest_version(root), 0, -1):
        proto = load_version(root, v)
        if proto.get("status") == "frozen":
            return proto
    return None


def _known(value: Any) -> bool:
    return value not in (None, "", "unknown", [], {})


def _write(root: Path, proto: dict[str, Any]) -> dict[str, Any]:
    errors = validate("protocol", proto)
    if errors:
        raise ValueError(f"invalid protocol: {errors}")
    protocol_dir(root)
    protocol_path(root, proto["version"]).write_text(
        yaml.safe_dump(proto, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    return proto


def draft(
    root: Path, fields: dict[str, Any] | None = None
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any] | None]:
    """Draft (or re-version) a protocol from supplied fields. No research
    question yet → a discovery plan and a protocol with status ``discovery``.
    """
    kind = study_kind(root)
    cfg = pack_config(kind)
    protocol_dir(root)
    findings: list[dict[str, Any]] = []
    fields = dict(fields or {})

    current = load_latest(root)
    base: dict[str, Any] = dict(current) if current else {}
    base.update(fields)

    proto: dict[str, Any] = {
        "schema_version": "0.2",
        "study_kind": kind,
        "version": latest_version(root) + 1,
    }
    if proto["version"] > 1:
        proto["previous"] = proto["version"] - 1
    for key in (
        "question",
        "scope",
        "language_scope",
        "period",
        "limits",
        "counter_evidence_rule",
        "resources",
        "inclusion",
        "exclusion",
        "synthesis_method",
        "saturation_rule",
        "concepts",
        "argument_structure",
        "assumptions",
        "change_reason",
    ):
        if key in base and _known(base[key]):
            proto[key] = base[key]

    if cfg and "saturation_rule" not in proto:
        proto["saturation_rule"] = cfg["saturation_default"]

    discovery: dict[str, Any] | None = None
    if not _known(proto.get("question")):
        proto["status"] = "discovery"
        discovery = _discovery_plan(root, kind, cfg)
        discovery_path(root).write_text(
            yaml.safe_dump(discovery, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )
    else:
        proto["status"] = "draft"

    # A scope change relative to the last frozen version needs a fresh G2.
    frozen = latest_frozen(root)
    if frozen and cfg:
        changed = [f for f in cfg["g2_fields"] if proto.get(f) != frozen.get(f)]
        if changed:
            proto["needs_gate"] = ["G2"]
            findings.append(
                {
                    "check_id": "protocol.changed_after_g1",
                    "severity": "blocker",
                    "reason": f"scope fields changed after G1: {', '.join(changed)}; needs G2",
                    "location": {},
                    "proposed_action": "",
                }
            )

    _write(root, proto)
    return proto, findings, discovery


def _discovery_plan(root: Path, kind: str, cfg: dict[str, Any] | None) -> dict[str, Any]:
    obj = json.loads((root / "object.json").read_text(encoding="utf-8"))
    topic = obj.get("title", "")
    load_policy()
    api_resources = [r for r in policy_resources() if r != "core"]
    required = cfg["required_fields"] if cfg else []
    unknowns = [f for f in required if f != "question"]
    return {
        "schema_version": "0.2",
        "study_kind": kind,
        "topic": topic,
        "initial_queries": [topic] if topic else [],
        "candidate_resources": api_resources,
        "unknowns": unknowns,
        "note": (
            "Discovery only: no results, matrix or synthesis until a question "
            "and a frozen protocol exist (H6)."
        ),
    }


def validate_for_freeze(root: Path) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Check the latest protocol against its pack's required fields."""
    proto = load_latest(root)
    findings: list[dict[str, Any]] = []
    if proto is None:
        findings.append(
            {
                "check_id": "protocol.missing",
                "severity": "blocker",
                "reason": "no protocol to freeze; run `rh protocol draft` first",
                "location": {},
                "proposed_action": "",
            }
        )
        return None, findings

    cfg = pack_config(proto["study_kind"])
    if cfg is None:
        findings.append(
            {
                "check_id": "protocol.no_pack",
                "severity": "blocker",
                "reason": (
                    f"no protocol pack for study_kind {proto['study_kind']!r} "
                    "(M2 covers literature, conceptual)"
                ),
                "location": {},
                "proposed_action": "",
            }
        )
        return proto, findings

    missing = [f for f in cfg["required_fields"] if not _known(proto.get(f))]
    if missing:
        findings.append(
            {
                "check_id": "protocol.required_missing",
                "severity": "blocker",
                "reason": f"protocol is missing required fields: {', '.join(missing)}",
                "location": {},
                "proposed_action": "",
            }
        )
    if proto.get("needs_gate"):
        findings.append(
            {
                "check_id": "protocol.changed_after_g1",
                "severity": "blocker",
                "reason": (
                    f"protocol v{proto['version']} needs "
                    f"{', '.join(proto['needs_gate'])} before it can be frozen"
                ),
                "location": {},
                "proposed_action": "",
            }
        )
    return proto, findings


def freeze(root: Path, lang: str) -> tuple[dict[str, Any] | None, str | None, list[dict[str, Any]]]:
    """Freeze the latest protocol and open the G1 approval request.

    Opening a request is not recording a decision (H14): the author records G1.
    """
    proto, findings = validate_for_freeze(root)
    if proto is None or any(f["severity"] == "blocker" for f in findings):
        return proto, None, findings

    proto["status"] = "frozen"
    _write(root, proto)
    _write_summary(root, proto, lang)

    from research_harness.gates.briefing import render
    from research_harness.gates.requests import open_request

    briefing = render(root, "G1", lang) + "\n\n" + _summary_text(proto, lang)
    ar_id = open_request(
        root,
        "G1",
        briefing_text=briefing,
        summary_path="protocol/summary.md",
        refs=[f"protocol:v{proto['version']}"],
    )
    return proto, ar_id, findings


def _summary_text(proto: dict[str, Any], lang: str) -> str:
    lab = {
        "question": ("Питання", "Question"),
        "scope": ("Межі", "Scope"),
        "inclusion": ("Критерії включення", "Inclusion"),
        "exclusion": ("Критерії виключення", "Exclusion"),
        "synthesis_method": ("Метод синтезу", "Synthesis method"),
        "saturation_rule": ("Правило насичення", "Saturation rule"),
        "limits": ("Обмеження", "Limits"),
    }
    i = 0 if lang == "uk" else 1
    head = "## Протокол" if lang == "uk" else "## Protocol"
    lines = [f"{head} (v{proto['version']}, {proto['study_kind']})", ""]
    for key, names in lab.items():
        if _known(proto.get(key)):
            val = proto[key]
            if isinstance(val, list):
                val = "; ".join(str(x) for x in val)
            lines.append(f"- **{names[i]}:** {val}")
    return "\n".join(lines) + "\n"


def _write_summary(root: Path, proto: dict[str, Any], lang: str) -> None:
    summary_path(root).write_text(_summary_text(proto, lang), encoding="utf-8")
