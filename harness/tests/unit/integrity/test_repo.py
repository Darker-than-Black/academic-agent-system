"""Repository / PR safety check (M3-14, FR-16, NFR-11, T41)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from research_harness.integrity import repo as r


def test_forbidden_hits_paths() -> None:
    paths = [
        "harness/src/research_harness/cli/repo.py",  # ok
        "research-harness-spec/holdout/F4-H/case.json",  # holdout
        ".env",
        "config/model-tiers.local.yaml",  # *.local.yaml basename
        "Projects/A-2026-001/work/scratch.txt",
    ]
    hits = set(r.forbidden_hits(paths))
    assert hits == {
        "research-harness-spec/holdout/F4-H/case.json",
        ".env",
        "config/model-tiers.local.yaml",
        "Projects/A-2026-001/work/scratch.txt",
    }


def test_secret_hits_and_holdout_skip(tmp_path: Path) -> None:
    (tmp_path / "clean.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "leak.env").write_text("ANTHROPIC_KEY=sk-ant-" + "a" * 40 + "\n", encoding="utf-8")
    # a secret under a holdout path must never be read (H1) -> not reported here
    hd = tmp_path / "holdout"
    hd.mkdir()
    (hd / "secret.txt").write_text("sk-ant-" + "b" * 40, encoding="utf-8")

    hits = r.secret_hits(tmp_path, ["clean.py", "leak.env", "holdout/secret.txt"])
    names = {(p, n) for p, n in hits}
    assert ("leak.env", "anthropic_key") in names
    assert all(p != "holdout/secret.txt" for p, _ in hits)
    assert all(p != "clean.py" for p, _ in hits)


def test_secret_hits_synthetic_sentinel_exempt(tmp_path: Path) -> None:
    """A placeholder whose token loudly declares itself synthetic is exempt (H6),
    but a real-looking token on another line is still reported (H8)."""
    # Both patterns tripped by the F5c fixture, every match sentinel-marked.
    (tmp_path / "f5c.py").write_text(
        'url = "https://example.test/collect?api_key=SYNTHETIC-NOT-A-REAL-KEY-000"\n'
        'example_token = "SYNTHETIC-PLACEHOLDER-DO-NOT-USE"\n',
        encoding="utf-8",
    )
    # Same pattern, one marked + one bare -> still reported (cannot be masked).
    # The bare token is assembled at runtime so this test's own source does not
    # trip the scanner that reads tracked .py files.
    bare = "https://api.x/y?api_key=" + "ZZZ0123456789abcdef0123"
    (tmp_path / "mixed.py").write_text(
        'fake = "api_key=SYNTHETIC-PLACEHOLDER-0000000000"\n' + f'real = "{bare}"\n',
        encoding="utf-8",
    )
    hits = r.secret_hits(tmp_path, ["f5c.py", "mixed.py"])
    assert all(p != "f5c.py" for p, _ in hits)
    assert ("mixed.py", "url_with_token") in hits


def test_holdout_hash_hits(tmp_path: Path) -> None:
    body = b"leaked holdout body\n"
    (tmp_path / "copied.txt").write_bytes(body)
    digest = hashlib.sha256(body).hexdigest()
    lock = tmp_path / "harness" / "evals"
    lock.mkdir(parents=True)
    (lock / "holdout.lock.json").write_text(
        json.dumps({"files": [{"path": "F4-H/x", "sha256": digest}]}), encoding="utf-8"
    )
    assert r.holdout_hash_hits(tmp_path, ["copied.txt"]) == ["copied.txt"]
    assert r.load_holdout_hashes(tmp_path) == {digest}


def test_findings_from_blockers() -> None:
    report = {
        "forbidden_paths": [".env"],
        "holdout_hashes": ["copied.txt"],
        "secrets": [("leak.env", "anthropic_key")],
    }
    f = r.findings_from(report)
    ids = {x["check_id"] for x in f}
    assert ids == {"repo.forbidden_path", "repo.holdout", "repo.secret"}
    assert all(x["severity"] == "blocker" for x in f)
