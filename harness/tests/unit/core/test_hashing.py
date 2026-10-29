"""Acceptance tests for the adapted hashing module (ADP-001, M1-02 DoD, T24)."""

from __future__ import annotations

from pathlib import Path

from research_harness.core import hashing


def test_crlf_and_lf_hash_equal(tmp_path: Path) -> None:
    lf = tmp_path / "lf.md"
    crlf = tmp_path / "crlf.md"
    lf.write_bytes(b"line one\nline two\n")
    crlf.write_bytes(b"line one\r\nline two\r\n")
    assert hashing.text_file_hash(lf) == hashing.text_file_hash(crlf)


def test_cr_only_normalized() -> None:
    assert hashing.text_hash(b"a\rb") == hashing.text_hash(b"a\nb")


def test_bom_ignored() -> None:
    assert hashing.text_hash(b"\xef\xbb\xbfhello") == hashing.text_hash(b"hello")


def test_canonical_json_independent_of_key_order() -> None:
    a = {"b": 1, "a": 2, "nested": {"y": 1, "x": 2}}
    b = {"a": 2, "nested": {"x": 2, "y": 1}, "b": 1}
    assert hashing.canonical_json_hash(a) == hashing.canonical_json_hash(b)


def test_canonical_json_unicode_not_escaped() -> None:
    # ensure_ascii=False: Cyrillic is hashed as UTF-8, not \uXXXX escapes.
    assert hashing.canonical_json_hash({"t": "Вступ"}) == hashing.canonical_json_hash(
        {"t": "Вступ"}
    )


def test_canonical_json_rejects_nan() -> None:
    import pytest

    with pytest.raises(ValueError):
        hashing.canonical_json_hash({"x": float("nan")})


def test_file_hash_dispatch(tmp_path: Path) -> None:
    md = tmp_path / "t.md"
    md.write_bytes(b"x\r\n")
    assert hashing.file_hash(md) == hashing.text_hash(b"x\r\n")
    binf = tmp_path / "t.bin"
    binf.write_bytes(b"x\r\n")
    assert hashing.file_hash(binf) == hashing.compute_sha256(binf)
    assert hashing.file_hash(md) != hashing.file_hash(binf)
