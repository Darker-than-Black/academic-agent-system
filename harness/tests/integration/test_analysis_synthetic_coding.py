"""Synthetic-participant guard, document coding, corpus export (M3-21;
analysis-sandbox.md; FR-59/FR-54; T65)."""

from __future__ import annotations

import json
from pathlib import Path

from research_harness.analysis import bibliometrics, coding, rows, runner, synthetic
from research_harness.sources import registry

_ROWS_SCRIPT = """\
import json, os
os.makedirs("outputs", exist_ok=True)
with open("outputs/rows.json", "w", encoding="utf-8") as fh:
    json.dump([{"variable_or_metric": "m", "value": 1, "unit": "n", "aggregation": "mean"}], fh)
"""


def _claims(root: Path, unit: str, claims: list[dict]) -> None:
    d = root / "manuscript" / unit
    d.mkdir(parents=True, exist_ok=True)
    (d / "claims.json").write_text(json.dumps({"claims": claims}, ensure_ascii=False), "utf-8")


def _script(root: Path) -> Path:
    p = root / "s.py"
    p.write_text(_ROWS_SCRIPT, encoding="utf-8")
    return p


# --- synthetic-participant guard (T65) -------------------------------------
def test_simulated_row_blocks_claim(tmp_path: Path) -> None:
    runner.run(tmp_path, _script(tmp_path), purpose="instrument_pilot")
    row = rows.load(tmp_path)[0]
    assert row["id"].startswith("RR-0001-")
    _claims(
        tmp_path,
        "U-AAAAAAAA",
        [
            {
                "id": "C-1",
                "kind": "own_numeric",
                "evidence": [{"type": "result_row", "id": row["id"]}],
            }
        ],
    )
    findings = synthetic.findings(tmp_path)
    assert len(findings) == 1
    assert findings[0]["check_id"] == "analysis.simulated_as_evidence"
    assert findings[0]["severity"] == "blocker"


def test_executed_row_does_not_block(tmp_path: Path) -> None:
    runner.run(tmp_path, _script(tmp_path), purpose="analysis")
    row = rows.load(tmp_path)[0]
    _claims(
        tmp_path,
        "U-AAAAAAAA",
        [
            {
                "id": "C-1",
                "kind": "own_numeric",
                "evidence": [{"type": "result_row", "id": row["id"]}],
            }
        ],
    )
    assert synthetic.findings(tmp_path) == []


# --- document coding (FR-54) -----------------------------------------------
def test_coding_verifies_quote(tmp_path: Path) -> None:
    doc = tmp_path / "doc.txt"
    doc.write_text("Teacher autonomy matters for assessment reform.", encoding="utf-8")
    rec = coding.add_code(
        tmp_path,
        codebook="cb1",
        code="autonomy",
        document_ref="doc.txt",
        quote="teacher autonomy matters",
        doc_file=str(doc),
    )
    assert rec["verified"] is True and rec["id"] == "CODE-0001"
    assert coding.quote_findings(tmp_path, "cb1") == []


def test_coding_flags_bad_quote(tmp_path: Path) -> None:
    doc = tmp_path / "doc.txt"
    doc.write_text("Teacher autonomy matters.", encoding="utf-8")
    coding.add_code(
        tmp_path,
        codebook="cb1",
        code="x",
        document_ref="doc.txt",
        quote="a sentence that is not in the document",
        doc_file=str(doc),
    )
    findings = coding.quote_findings(tmp_path, "cb1")
    assert len(findings) == 1 and findings[0]["check_id"] == "coding.quote_mismatch"
    summary = coding.summary(tmp_path, "cb1")
    assert summary["total"] == 1 and summary["unverified"] == ["CODE-0001"]


# --- corpus bibliometrics export (FR-54 p.3) -------------------------------
def test_corpus_export(tmp_path: Path) -> None:
    registry.add_records(
        tmp_path,
        [{"bib_key": "k1", "author": "Коваль, І.", "title": "T", "container": "V", "year": "2020"}],
    )
    report = bibliometrics.export(tmp_path)
    assert report["n"] == 1
    out = tmp_path / "analysis" / "data" / "corpus-metadata.json"
    assert out.is_file()
    assert str(json.loads(out.read_text(encoding="utf-8"))[0]["year"]) == "2020"
