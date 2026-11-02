"""P3-1: thesis regulatory slots block `verified` until the author fills them."""

from __future__ import annotations

from pathlib import Path

import yaml

from research_harness.thesis import regulatory as reg

_PACK = Path(__file__).resolve().parents[2] / "rulepacks" / "ua-mon-phd"


def _write(tmp_path: Path, data: dict) -> Path:
    (tmp_path / "regulatory.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
    return tmp_path


def test_shipped_slots_default_to_unknown_and_block() -> None:
    f = reg.findings(_PACK)
    assert f, "shipped regulatory.yaml must block verified until filled"
    assert all(x["check_id"] == "thesis.regulatory_unfilled" for x in f)
    assert all(x["severity"] == "blocker" for x in f)
    # Every required slot is reported while unknown.
    assert len(f) == len(reg.REQUIRED_SLOTS)


def test_missing_file_blocks_all_required(tmp_path: Path) -> None:
    assert len(reg.findings(tmp_path)) == len(reg.REQUIRED_SLOTS)


def test_fully_filled_passes(tmp_path: Path) -> None:
    root = _write(
        tmp_path,
        {
            "volume_limits": {
                "main_text_author_sheets_min": 6.0,
                "main_text_author_sheets_max": 9.0,
                "source": "постанова КМУ № 1240, п. X",
            },
            "self_plagiarism_exclusion": {"rule": "…", "source": "постанова № 1240, п. Y"},
            "local_rules_udu": {
                "onp_applies": True,
                "onp_source": "ОНП УДУ, розд. Z",
                "ai_regulation_applies": False,
                "ai_regulation_source": "unknown",  # not required: flag is false
            },
        },
    )
    assert reg.findings(root) == []


def test_flag_true_requires_source(tmp_path: Path) -> None:
    root = _write(
        tmp_path,
        {
            "volume_limits": {
                "main_text_author_sheets_min": 6.0,
                "main_text_author_sheets_max": 9.0,
                "source": "s",
            },
            "self_plagiarism_exclusion": {"rule": "r", "source": "s"},
            "local_rules_udu": {
                "onp_applies": True,
                "onp_source": "unknown",  # required because the flag is true
                "ai_regulation_applies": False,
                "ai_regulation_source": "unknown",
            },
        },
    )
    locs = {x["location"]["locator"] for x in reg.findings(root)}
    assert locs == {"local_rules_udu.onp_source"}
