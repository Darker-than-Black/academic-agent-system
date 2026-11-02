"""Figures built from rows, rebuilt and invalidated (M3-20; analysis-sandbox.md;
FR-18; T18). The plotting script runs with the network off."""

from __future__ import annotations

from pathlib import Path

import pytest

from research_harness.analysis import figures, rows
from research_harness.core.errors import BlockedError

_PLOT = """\
import json, os
with open("rows.json", encoding="utf-8") as fh:
    data = json.load(fh)
os.makedirs("outputs", exist_ok=True)
with open("outputs/figure.svg", "w", encoding="utf-8") as fh:
    fh.write("<svg><!-- %d rows --></svg>" % len(data))
"""


def _seed_rows(root: Path) -> str:
    created = rows.append_from_output(
        root,
        "R-0001",
        [{"variable_or_metric": "accuracy", "value": 0.95, "unit": "ratio", "aggregation": "mean"}],
    )
    return created[0]["id"]


def _object(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path
    rid = _seed_rows(root)
    (root / "analysis" / "scripts").mkdir(parents=True)
    (root / "analysis" / "scripts" / "plot.py").write_text(_PLOT, encoding="utf-8")
    return root, rid


def test_build_and_fresh(tmp_path: Path) -> None:
    root, rid = _object(tmp_path)
    rec = figures.add(root, script="analysis/scripts/plot.py", row_ids=[rid])
    assert rec["id"] == "FIG-001" and rec["built_at"] is None
    assert figures.is_stale(root, "FIG-001") is True  # not built yet

    built = figures.build(root, "FIG-001")
    assert built["built_at"] is not None and built["data_sha256"]
    assert (figures.figures_dir(root) / "FIG-001.svg").is_file()
    assert figures.is_stale(root, "FIG-001") is False
    assert figures.stale_findings(root) == []


def test_script_edit_makes_stale(tmp_path: Path) -> None:
    root, rid = _object(tmp_path)
    figures.add(root, script="analysis/scripts/plot.py", row_ids=[rid])
    figures.build(root, "FIG-001")
    assert figures.is_stale(root, "FIG-001") is False

    # Editing the plotting script invalidates the figure (FR-18).
    (root / "analysis" / "scripts" / "plot.py").write_text(_PLOT + "# tweak\n", encoding="utf-8")
    assert figures.is_stale(root, "FIG-001") is True
    findings = figures.stale_findings(root)
    assert findings and findings[0]["check_id"] == "analysis.figure_stale"

    figures.build(root, "FIG-001")  # rebuild clears it
    assert figures.is_stale(root, "FIG-001") is False


def test_missing_row_makes_stale_and_build_refuses(tmp_path: Path) -> None:
    root, rid = _object(tmp_path)
    figures.add(root, script="analysis/scripts/plot.py", row_ids=[rid])
    figures.build(root, "FIG-001")

    # Drop the referenced row from the store.
    rows.rows_path(root).write_text("", encoding="utf-8")
    assert figures.is_stale(root, "FIG-001") is True
    with pytest.raises(BlockedError):
        figures.build(root, "FIG-001")


def test_unknown_figure_refuses(tmp_path: Path) -> None:
    with pytest.raises(BlockedError):
        figures.build(tmp_path, "FIG-999")
