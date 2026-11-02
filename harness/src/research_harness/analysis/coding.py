"""Qualitative coding of public documents (M3-21, FR-54).

A codebook holds codes; each coded excerpt carries a locator and the quote, and
the quote is verified against the source document's text — a quote that is not
found there is a finding (``coding.quote_mismatch``), never silently accepted
(H6/H7). The document text is not copied into the repo (H8); only a short quote,
the locator and the document hash are stored.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import yaml

from research_harness.core.clock import default_clock
from research_harness.core.hashing import file_hash
from research_harness.schemas import validate

_WS = re.compile(r"\s+")


def coding_dir(root: Path, codebook: str) -> Path:
    return root / "analysis" / "coding" / codebook


def codebook_path(root: Path, codebook: str) -> Path:
    return coding_dir(root, codebook) / "codebook.yaml"


def codes_path(root: Path, codebook: str) -> Path:
    return coding_dir(root, codebook) / "codes.jsonl"


def _norm(text: str) -> str:
    return _WS.sub(" ", unicodedata.normalize("NFC", text or "")).strip().casefold()


def ensure_codebook(root: Path, codebook: str) -> None:
    path = codebook_path(root, codebook)
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            yaml.safe_dump({"id": codebook, "codes": []}, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )


def load_codes(root: Path, codebook: str) -> list[dict[str, Any]]:
    path = codes_path(root, codebook)
    if not path.is_file():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def _next_id(existing: list[dict[str, Any]]) -> str:
    nums = [int(c["id"].split("-")[1]) for c in existing if c.get("id", "").startswith("CODE-")]
    return f"CODE-{max(nums, default=0) + 1:04d}"


def verify_quote(quote: str, doc_text: str) -> bool:
    return _norm(quote) in _norm(doc_text)


def add_code(
    root: Path,
    *,
    codebook: str,
    code: str,
    document_ref: str,
    quote: str,
    locator: str = "",
    doc_file: str | None = None,
) -> dict[str, Any]:
    """Record a coded excerpt; verify the quote against the document text."""
    ensure_codebook(root, codebook)
    existing = load_codes(root, codebook)

    verified = False
    doc_sha = "unknown"
    if doc_file:
        path = root / doc_file if (root / doc_file).is_file() else Path(doc_file)
        if path.is_file():
            doc_sha = file_hash(path)
            verified = verify_quote(quote, path.read_text(encoding="utf-8"))

    record = {
        "schema_version": "0.2",
        "id": _next_id(existing),
        "created_at": default_clock().now_rfc3339(),
        "code": code,
        "document_ref": document_ref,
        "locator": locator,
        "quote": quote,
        "doc_sha256": doc_sha,
        "verified": verified,
    }
    errors = validate("code", record)
    if errors:
        raise ValueError(f"invalid code record: {errors}")
    with codes_path(root, codebook).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def quote_findings(root: Path, codebook: str) -> list[dict[str, Any]]:
    """``coding.quote_mismatch`` (major) for each code whose quote is unverified."""
    out: list[dict[str, Any]] = []
    for c in load_codes(root, codebook):
        if not c.get("verified"):
            out.append(
                {
                    "check_id": "coding.quote_mismatch",
                    "severity": "major",
                    "reason": f"code {c['id']} quote not verified against {c['document_ref']}",
                    "location": {"code": c["id"], "document": c["document_ref"]},
                    "observed": c.get("locator"),
                    "proposed_action": "Fix the quote or locator to match the document text.",
                }
            )
    return out


def summary(root: Path, codebook: str) -> dict[str, Any]:
    codes = load_codes(root, codebook)
    freq: dict[str, int] = {}
    for c in codes:
        freq[c["code"]] = freq.get(c["code"], 0) + 1
    return {
        "codebook": codebook,
        "total": len(codes),
        "frequencies": dict(sorted(freq.items())),
        "unverified": [c["id"] for c in codes if not c.get("verified")],
    }
