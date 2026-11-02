"""Asset registry and rights check (M3-12, FR-17)."""

from __future__ import annotations

from pathlib import Path

import pytest

from research_harness.core.errors import InvalidInputError
from research_harness.integrity import assets as a


def _file(root: Path, rel: str, body: bytes = b"data") -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(body)


def test_add_list_and_ids(tmp_path: Path) -> None:
    _file(tmp_path, "figures/f1.png")
    _file(tmp_path, "figures/f2.png", b"other")
    r1 = a.add_asset(
        tmp_path,
        "figures/f1.png",
        origin="third_party",
        rights_status="licensed",
        kind="figure",
        license="CC-BY-4.0",
    )
    r2 = a.add_asset(
        tmp_path,
        "figures/f2.png",
        origin="own_generated",
        rights_status="own",
        kind="figure",
        generated_from_rows=["RR-0001-0001"],
    )
    assert r1["id"] == "AS-001" and r2["id"] == "AS-002"
    assert len(r1["sha256"]) == 64 and r1["sha256"] != r2["sha256"]
    assert len(a.load(tmp_path)) == 2


def test_rights_findings_block_thirdparty_without_rights(tmp_path: Path) -> None:
    _file(tmp_path, "x.png")
    a.add_asset(tmp_path, "x.png", origin="third_party", rights_status="unknown", kind="image")
    f = a.rights_findings(tmp_path)
    assert len(f) == 1 and f[0]["check_id"] == "integrity.asset_rights"
    assert f[0]["severity"] == "blocker"


def test_own_and_licensed_pass(tmp_path: Path) -> None:
    _file(tmp_path, "a.png")
    _file(tmp_path, "b.png", b"b")
    a.add_asset(tmp_path, "a.png", origin="own_data", rights_status="own", kind="image")
    a.add_asset(tmp_path, "b.png", origin="third_party", rights_status="licensed", kind="image")
    assert a.rights_findings(tmp_path) == []


def test_permission_documented_requires_doc(tmp_path: Path) -> None:
    _file(tmp_path, "m.png")
    with pytest.raises(InvalidInputError):
        a.add_asset(
            tmp_path,
            "m.png",
            origin="third_party",
            rights_status="permission_documented",
            permission_doc_path="perm/none.pdf",
        )
    _file(tmp_path, "perm/ok.pdf", b"pdf")
    rec = a.add_asset(
        tmp_path,
        "m.png",
        origin="third_party",
        rights_status="permission_documented",
        permission_doc_path="perm/ok.pdf",
    )
    assert rec["permission_doc"]["path"] == "perm/ok.pdf"


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(InvalidInputError):
        a.add_asset(tmp_path, "nope.png", origin="own_data", rights_status="own")
