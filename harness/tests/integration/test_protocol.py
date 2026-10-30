"""Protocol draft/freeze/version, packs, G1 handoff (M2-05): T01, T03."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from research_harness.cli import protocol as cli_protocol
from research_harness.gates import requests
from research_harness.lab import protocol as proto_mod
from research_harness.rules.loader import lint_pack
from research_harness.workspace.objects import create_object
from research_harness.workspace.workspace import Workspace

_RULEPACKS = Path(__file__).resolve().parents[2] / "rulepacks"

_FIELDS = {
    "question": "How does formative assessment affect achievement?",
    "scope": "Secondary education",
    "language_scope": ["uk", "en"],
    "period": "2010-2025",
    "resources": [{"resource": "eric", "queries": ["formative assessment"]}],
    "inclusion": ["peer-reviewed"],
    "exclusion": ["non-education"],
    "synthesis_method": "narrative",
    "counter_evidence_rule": "seek disconfirming studies",
    "limits": ["uk/en only"],
}


def _lit_object(tmp_path: Path):
    ws = Workspace.init(tmp_path / "Projects")
    return create_object(
        ws, title="Протокол", kind="article", document_kind="article", study_kind="literature"
    )


def test_packs_lint_clean() -> None:
    assert lint_pack(_RULEPACKS / "literature-narrative") == []
    assert lint_pack(_RULEPACKS / "conceptual") == []


def test_topic_only_gets_discovery_plan(tmp_path: Path) -> None:  # T01
    _oid, folder = _lit_object(tmp_path)
    proto, findings, discovery = proto_mod.draft(folder, {})
    assert proto["status"] == "discovery" and not findings
    assert discovery is not None and discovery["initial_queries"]
    assert "synthesis_method" in discovery["unknowns"]
    assert proto_mod.discovery_path(folder).is_file()
    # Nothing invented: no inclusion, synthesis or results fabricated (H6).
    assert "inclusion" not in proto and "synthesis_method" not in proto


def test_draft_then_freeze_opens_g1(tmp_path: Path) -> None:
    _oid, folder = _lit_object(tmp_path)
    proto, findings, _ = proto_mod.draft(folder, dict(_FIELDS))
    assert proto["status"] == "draft" and not findings
    # default saturation came from the pack
    assert proto["saturation_rule"]["batch_size"] == 10
    frozen, ar_id, f2 = proto_mod.freeze(folder, "uk")
    assert ar_id is not None and not f2
    assert frozen["status"] == "frozen"
    assert proto_mod.summary_path(folder).is_file()
    assert requests.open_requests(folder, "G1")


def test_freeze_blocked_when_required_field_missing(tmp_path: Path) -> None:
    _oid, folder = _lit_object(tmp_path)
    partial = {k: v for k, v in _FIELDS.items() if k != "synthesis_method"}
    proto_mod.draft(folder, partial)
    proto, ar_id, findings = proto_mod.freeze(folder, "uk")
    assert ar_id is None
    assert any(f["check_id"] == "protocol.required_missing" for f in findings)
    assert not requests.open_requests(folder, "G1")


def test_change_after_g1_versions_and_needs_g2(tmp_path: Path) -> None:  # T03
    _oid, folder = _lit_object(tmp_path)
    proto_mod.draft(folder, dict(_FIELDS))
    proto_mod.freeze(folder, "uk")  # v1 frozen at G1
    assert proto_mod.protocol_path(folder, 1).is_file()

    v2, findings, _ = proto_mod.draft(folder, {"inclusion": ["peer-reviewed", "grey-lit"]})
    assert v2["version"] == 2
    assert proto_mod.protocol_path(folder, 1).is_file()  # v1 kept
    assert v2["needs_gate"] == ["G2"]
    assert any(f["check_id"] == "protocol.changed_after_g1" for f in findings)

    # v2 cannot be frozen until G2 is recorded.
    _p, ar_id, f2 = proto_mod.freeze(folder, "uk")
    assert ar_id is None and any(f["check_id"] == "protocol.changed_after_g1" for f in f2)


def test_cli_freeze_hands_g1_to_author(tmp_path: Path) -> None:
    _oid, folder = _lit_object(tmp_path)
    proto_mod.draft(folder, dict(_FIELDS))
    args = SimpleNamespace(object=None, root=str(folder), workspace=None, protocol_action="freeze")
    env, code = cli_protocol.route(args, "uk")
    assert code == 0
    na = env["next_actions"][0]
    assert na["who"] == "author" and "gate record G1" in na["command"]
