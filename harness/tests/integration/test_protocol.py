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


def test_draft_invalid_fields_blocks_cleanly(tmp_path: Path) -> None:  # Finding 3
    # A mistyped field (list where a string belongs) must surface as a blocker
    # finding, not a raw ValueError, and no protocol file is written.
    _oid, folder = _lit_object(tmp_path)
    bad = dict(_FIELDS)
    bad["scope"] = ["this", "should", "be", "a", "string"]
    proto, findings, _ = proto_mod.draft(folder, bad)
    assert any(f["check_id"] == "protocol.invalid_fields" for f in findings)
    assert all(f["severity"] in {"blocker", "major", "minor", "info"} for f in findings)
    assert proto_mod.latest_version(folder) == 0  # nothing persisted


def test_draft_warns_when_study_kind_has_no_pack(tmp_path: Path) -> None:  # Finding 2
    # A profile with no protocol pack yet (mixed) must not degrade silently:
    # draft still writes, but returns a `protocol.no_pack` major warning.
    ws = Workspace.init(tmp_path / "Projects")
    _oid, folder = create_object(
        ws, title="Mixed", kind="article", document_kind="article", study_kind="mixed"
    )
    proto, findings, _ = proto_mod.draft(folder, dict(_FIELDS))
    no_pack = [f for f in findings if f["check_id"] == "protocol.no_pack"]
    assert no_pack and no_pack[0]["severity"] == "major"
    assert not any(f["severity"] == "blocker" for f in findings)
    assert proto_mod.latest_version(folder) == 1  # degraded, still drafted


def test_draft_no_pack_warning_absent_for_supported_kind(tmp_path: Path) -> None:  # Finding 2
    _oid, folder = _lit_object(tmp_path)
    _proto, findings, _ = proto_mod.draft(folder, dict(_FIELDS))
    assert not any(f["check_id"] == "protocol.no_pack" for f in findings)


def test_cli_draft_missing_file_returns_blocked_envelope(tmp_path: Path) -> None:  # Finding 3
    oid, folder = _lit_object(tmp_path)
    args = SimpleNamespace(
        protocol_action="draft",
        file=str(tmp_path / "nope.yaml"),
        object=oid,
        workspace=str(tmp_path / "Projects"),
        root=None,
    )
    env, code = cli_protocol.route(args, "uk")
    assert code == 3 and env["status"] == "blocked"
    assert any(f["check_id"] == "protocol.file_invalid" for f in env["findings"])
    assert proto_mod.latest_version(folder) == 0


def test_cli_draft_non_mapping_file_returns_blocked_envelope(tmp_path: Path) -> None:  # Finding 3
    oid, folder = _lit_object(tmp_path)
    bad = tmp_path / "fields.yaml"
    bad.write_text("- just\n- a\n- list\n", encoding="utf-8")
    args = SimpleNamespace(
        protocol_action="draft",
        file=str(bad),
        object=oid,
        workspace=str(tmp_path / "Projects"),
        root=None,
    )
    env, code = cli_protocol.route(args, "uk")
    assert code == 3 and env["status"] == "blocked"
    assert any(f["check_id"] == "protocol.file_invalid" for f in env["findings"])
    assert "mapping" in env["findings"][0]["reason"]


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
