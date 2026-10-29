"""Content hashing (02 §1.3).

Adapted from AutoResearchClaw (MIT)
  @ be4ba4755bf1b52220f25e13b2293b5956590070 : researchclaw/hitl/checksums.py
Changes: kept the streaming SHA-256 read loop; added canonical-JSON hashing
(sorted keys, no NaN/Infinity), text-file normalization (strip UTF-8 BOM,
convert CRLF/CR to LF before hashing), and an extension-based file dispatch;
dropped the stage-manifest helpers (not used here). See adoption record ADP-001
in harness/third_party/manifest.json.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

_CHUNK = 8192

# Extensions hashed as text (BOM-stripped, newline-normalized); 02 §1.3.
TEXT_SUFFIXES = frozenset({".md", ".yaml", ".yml", ".bib", ".ris", ".txt", ".csv", ".json"})

_UTF8_BOM = b"\xef\xbb\xbf"


def compute_sha256(path: str | Path) -> str:
    """SHA-256 of a file's raw bytes, read in chunks (streaming)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


binary_file_hash = compute_sha256


def normalize_text_bytes(data: bytes) -> bytes:
    """Strip a leading UTF-8 BOM and convert CRLF/CR to LF (02 §1.3).

    Content is not Unicode-normalized — that would alter the author's text.
    """
    if data.startswith(_UTF8_BOM):
        data = data[len(_UTF8_BOM) :]
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def text_hash(data: bytes) -> str:
    """SHA-256 of normalized text bytes."""
    return hashlib.sha256(normalize_text_bytes(data)).hexdigest()


def text_file_hash(path: str | Path) -> str:
    """SHA-256 of a text file after BOM strip and newline normalization."""
    return text_hash(Path(path).read_bytes())


def canonical_json_bytes(obj: Any) -> bytes:
    """Canonical JSON encoding: sorted keys, compact, UTF-8, no NaN/Infinity."""
    text = json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return text.encode("utf-8")


def canonical_json_hash(obj: Any) -> str:
    """SHA-256 of an object's canonical JSON form (independent of key order)."""
    return hashlib.sha256(canonical_json_bytes(obj)).hexdigest()


def file_hash(path: str | Path) -> str:
    """Hash a file: text rules for known text suffixes, raw bytes otherwise."""
    path = Path(path)
    if path.suffix.lower() in TEXT_SUFFIXES:
        return text_file_hash(path)
    return compute_sha256(path)
