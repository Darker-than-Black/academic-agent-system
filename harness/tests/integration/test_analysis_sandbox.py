"""Analysis sandbox scaffolding and dataset registry (M3-18; analysis-sandbox.md;
FR-57/FR-39/NFR-08). Registry admits nothing without terms; sandbox never
pretends — network is a namespace or a Python guard."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from research_harness.analysis import datasets, project, sandbox


def test_dataset_add_with_terms_is_admitted(tmp_path: Path) -> None:
    terms = tmp_path / "terms.txt"
    terms.write_text("CC-BY 4.0", encoding="utf-8")
    rec = datasets.add(
        tmp_path, name="pisa2022", version="2022", url="https://ex/pisa", terms=str(terms)
    )
    assert rec["id"] == "D-001" and rec["storage"] == "copy"
    assert datasets.admitted(rec) is True
    assert datasets.terms_findings(tmp_path, ["D-001"]) == []
    assert len(datasets.load(tmp_path)) == 1


def test_dataset_without_terms_blocks(tmp_path: Path) -> None:
    rec = datasets.add(tmp_path, name="noterms", version="1")
    assert datasets.admitted(rec) is False
    findings = datasets.terms_findings(tmp_path, [rec["id"]])
    assert len(findings) == 1
    assert findings[0]["check_id"] == "analysis.dataset_terms_missing"
    assert findings[0]["severity"] == "blocker"


def test_dataset_copies_and_hashes_local_file(tmp_path: Path) -> None:
    src = tmp_path / "raw.csv"
    src.write_text("a,b\n1,2\n", encoding="utf-8")
    terms = tmp_path / "t.txt"
    terms.write_text("terms", encoding="utf-8")
    rec = datasets.add(tmp_path, name="local", version="1", terms=str(terms), from_path=str(src))
    assert rec["sha256"] != "unknown" and len(rec["sha256"]) == 64
    assert (datasets.data_dir(tmp_path) / "local").is_file()


def test_analysis_init_writes_pinned_pyproject(tmp_path: Path) -> None:
    report = project.init(tmp_path)
    assert report["created"] is True
    text = project.pyproject_path(tmp_path).read_text(encoding="utf-8")
    for name, ver in project.BASE_PACKAGES:
        assert f"{name}=={ver}" in text
    # Idempotent: a second init keeps the (possibly edited) pyproject.
    assert project.init(tmp_path)["created"] is False


def test_sandbox_capability_is_real_not_pretend() -> None:
    caps = sandbox.capabilities()
    assert caps.network in ("disabled", "guard_only")
    assert isinstance(caps.namespace, bool)


def test_network_guard_blocks_outbound(tmp_path: Path) -> None:
    sandbox.write_guard(tmp_path)
    script = tmp_path / "try_net.py"
    script.write_text(
        "import socket\n"
        "try:\n"
        "    socket.create_connection(('93.184.216.34', 80), timeout=2)\n"
        "    print('CONNECTED')\n"
        "except OSError as e:\n"
        "    print('BLOCKED')\n",
        encoding="utf-8",
    )
    result = subprocess.run(  # noqa: S603
        [sys.executable, str(script)],
        cwd=tmp_path,
        env={"PYTHONPATH": str(tmp_path)},
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert "BLOCKED" in result.stdout
