"""Validator framework, schema/ref checks, and the `rh validate` CLI."""

from __future__ import annotations

import json
from pathlib import Path

from research_harness.cli.main import main as rh_main
from research_harness.validate import has_blocker, run_checks
from research_harness.validate.framework import ValidationContext, finding
from research_harness.validate.ref_checks import check_refs, collect_refs
from research_harness.validate.schema_checks import validate_record

EXAMPLES = Path(__file__).parent / "examples"


def test_finding_builder_rejects_bad_severity() -> None:
    import pytest

    with pytest.raises(ValueError):
        finding(check_id="c", severity="catastrophe", reason="x")


def test_has_blocker() -> None:
    assert has_blocker([finding(check_id="c", severity="blocker", reason="r")])
    assert not has_blocker([finding(check_id="c", severity="minor", reason="r")])


def test_validate_record_reports_schema_errors() -> None:
    good = json.loads((EXAMPLES / "object" / "valid-1.json").read_text(encoding="utf-8"))
    assert validate_record("object", good) == []
    bad = dict(good)
    bad.pop("kind")
    findings = validate_record("object", bad, ref="object:A-2026-001/object")
    assert findings and findings[0]["severity"] == "blocker"


def test_collect_and_check_refs() -> None:
    claim = json.loads((EXAMPLES / "claim" / "valid-1.json").read_text(encoding="utf-8"))
    claim["evidence"] = [{"type": "excerpt", "id": "E-00001"}]
    claim["dependencies"] = [{"ref": "source:S-0001", "sha256": "a" * 64}]
    refs = set(collect_refs(claim))
    assert refs == {"excerpt:E-00001", "source:S-0001"}

    records = {"claim:C-1": claim}
    assert check_refs(records, {"excerpt:E-00001", "source:S-0001"}) == []
    unresolved = check_refs(records, {"excerpt:E-00001"})
    assert len(unresolved) == 1 and unresolved[0]["severity"] == "blocker"


def test_run_checks_schema_scope() -> None:
    bad = json.loads((EXAMPLES / "source" / "valid-1.json").read_text(encoding="utf-8"))
    bad.pop("bib_key")
    ctx = ValidationContext()
    ctx.extra["records_to_validate"] = [{"schema": "source", "ref": "source:S-0001", "record": bad}]
    findings = run_checks(["schema"], ctx)
    assert has_blocker(findings)


def test_cli_validate_passes(tmp_path: Path, capsys) -> None:
    good = EXAMPLES / "object" / "valid-1.json"
    rc = rh_main(["validate", "--scope", "schema", "--schema", "object", "--file", str(good)])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["status"] == "ok"
    assert out["data"]["finding_count"] == 0


def test_cli_validate_blocks_on_bad_file(tmp_path: Path, capsys) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text('{"schema_version":"0.2"}', encoding="utf-8")
    rc = rh_main(["validate", "--scope", "schema", "--schema", "object", "--file", str(bad)])
    out = json.loads(capsys.readouterr().out)
    assert rc == 3
    assert out["status"] == "blocked"
    assert out["data"]["finding_count"] >= 1
