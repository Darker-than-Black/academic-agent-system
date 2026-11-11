"""Overlap check against the author's own corpus (integrity.md; M3-10, FR-30).

Deterministic, no LLM. Compares the current unit text against the author corpus
(`_author/corpus/`) by normalized word shingles (Cyrillic- and Latin-aware) and
reports contiguous overlapping fragments of at least ``min_fragment_words``.
An empty corpus yields ``result: unknown`` (never a clean pass — NFR-14).

Rule-pack thresholds (ua-mon-phd / ua-fahove-b) refine severity and are wired in
M3-23; the defaults here are conservative.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from research_harness.core import tokenize_uk
from research_harness.core.clock import default_clock
from research_harness.core.hashing import text_hash
from research_harness.schemas import validate
from research_harness.structure import ops
from research_harness.summaries.deterministic import body_of

_WORD = re.compile(r"[^\W_]+", re.UNICODE)

SHINGLE_SIZE = 8
MIN_FRAGMENT_WORDS = 20
HIGH_RATIO = 0.30
# Word tokens are normalized by research_harness.core.tokenize_uk: lemma when the
# optional Ukrainian analyzer is installed (inflection-insensitive overlap),
# casefold otherwise (identical to the prior behavior). P2-2.
NORMALIZATION = "tokenize_uk_normalize"
_CORPUS_GLOBS = ("*.txt", "*.md")


def _tokens(text: str) -> tuple[list[str], list[tuple[int, int]]]:
    words: list[str] = []
    spans: list[tuple[int, int]] = []
    for m in _WORD.finditer(text):
        words.append(tokenize_uk.normalize(m.group(0)))
        spans.append((m.start(), m.end()))
    return words, spans


def shingles(words: list[str], n: int) -> set[tuple[str, ...]]:
    return (
        {tuple(words[i : i + n]) for i in range(len(words) - n + 1)} if len(words) >= n else set()
    )


def load_corpus(corpus_dir: Path) -> dict[str, str]:
    """Author corpus documents (``_author/corpus/``) keyed by relative path."""
    out: dict[str, str] = {}
    if not corpus_dir.is_dir():
        return out
    for pattern in _CORPUS_GLOBS:
        for path in sorted(corpus_dir.rglob(pattern)):
            out[str(path.relative_to(corpus_dir))] = path.read_text(encoding="utf-8")
    return out


def _corpus_shingle_index(corpus: dict[str, str], n: int) -> dict[tuple[str, ...], str]:
    index: dict[tuple[str, ...], str] = {}
    for doc_id, text in corpus.items():
        words, _ = _tokens(text)
        for sh in shingles(words, n):
            index.setdefault(sh, doc_id)
    return index


def load_source_corpus(root: Path) -> dict[str, str]:
    """Cited-source fulltext keyed by source id (ADR-026).

    Reads ``sources/pagetext/<S-id>.jsonl`` — gitignored foreign fulltext, read
    only at runtime (H8); the report stores source ids and overlap counts, never
    the source text. A missing directory yields an empty corpus.
    """
    out: dict[str, str] = {}
    pagetext_dir = root / "sources" / "pagetext"
    if not pagetext_dir.is_dir():
        return out
    for path in sorted(pagetext_dir.glob("*.jsonl")):
        pages: list[str] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            text = json.loads(line).get("text", "")
            if text:
                pages.append(text)
        if pages:
            out[path.stem] = "\n".join(pages)
    return out


def find_matches(
    unit_id: str,
    text: str,
    corpus_index: dict[tuple[str, ...], str],
    *,
    corpus_kind: str = "author",
    n: int = SHINGLE_SIZE,
    min_words: int = MIN_FRAGMENT_WORDS,
) -> list[dict[str, Any]]:
    """Maximal contiguous runs of corpus-matching shingles, >= min_words long."""
    words, spans = _tokens(text)
    total = len(words)
    covered: list[str | None] = [
        corpus_index.get(tuple(words[i : i + n])) for i in range(max(0, total - n + 1))
    ]
    matches: list[dict[str, Any]] = []
    i = 0
    while i < len(covered):
        if covered[i] is None:
            i += 1
            continue
        j = i
        while j + 1 < len(covered) and covered[j + 1] is not None:
            j += 1
        last_word = j + n - 1
        overlap_words = last_word - i + 1
        if overlap_words >= min_words:
            char_start, char_end = spans[i][0], spans[last_word][1]
            ratio = round(overlap_words / total, 4) if total else 0.0
            matches.append(
                {
                    "unit_id": unit_id,
                    "char_start": char_start,
                    "char_end": char_end,
                    "corpus_doc_id": covered[i],
                    "corpus_kind": corpus_kind,
                    "shingle_size": n,
                    "overlap_words": overlap_words,
                    "overlap_ratio": ratio,
                    "cited": False,
                    "severity": "major" if ratio >= HIGH_RATIO else "minor",
                }
            )
        i = j + 1
    return matches


def _bodies(root: Path, unit: str | None) -> dict[str, str]:
    folders = ops.current_folders(root)
    out: dict[str, str] = {}
    for uid, folder in folders.items():
        if unit and uid != unit:
            continue
        tf = folder / "text.md"
        if tf.is_file():
            out[uid] = body_of(tf.read_text(encoding="utf-8"))
    return out


def run(
    root: Path,
    *,
    unit: str | None = None,
    corpus_dir: Path | None = None,
    against: str = "corpus",
    n: int = SHINGLE_SIZE,
    min_words: int = MIN_FRAGMENT_WORDS,
) -> dict[str, Any]:
    """Build an overlap report (ADR-026).

    ``against`` selects the corpora: ``corpus`` (the author corpus — self-overlap,
    FR-30), ``sources`` (cited-source fulltext — copying from a source), or
    ``both``. An empty *author* corpus never yields a clean pass when the author
    corpus is one of the selected targets (NFR-14): the result stays ``unknown``.
    """
    author_selected = against in ("corpus", "both")
    source_selected = against in ("sources", "both")
    author_corpus = load_corpus(corpus_dir) if (author_selected and corpus_dir) else {}
    source_corpus = load_source_corpus(root) if source_selected else {}

    combined = {
        **{f"author:{k}": v for k, v in author_corpus.items()},
        **{f"source:{k}": v for k, v in source_corpus.items()},
    }
    report: dict[str, Any] = {
        "schema_version": "0.2",
        "run_id": "OV-" + default_clock().now_rfc3339().replace(":", "").replace("-", ""),
        "against": against,
        "corpus_index_sha256": text_hash(
            "\n".join(combined[k] for k in sorted(combined)).encode("utf-8")
        ),
        "rule_refs": [],
        "method": {
            "normalization": NORMALIZATION,
            "shingle_size": n,
            "min_fragment_words": min_words,
        },
        "matches": [],
        "limitations": ["citation detection not applied (cited=false)"],
        "result": "ok",
    }
    have_author = author_selected and bool(author_corpus)
    have_source = source_selected and bool(source_corpus)
    bodies = _bodies(root, unit) if (have_author or have_source) else {}
    if have_author:
        index = _corpus_shingle_index(author_corpus, n)
        for uid in sorted(bodies):
            report["matches"].extend(
                find_matches(
                    uid, bodies[uid], index, corpus_kind="author", n=n, min_words=min_words
                )
            )
    if have_source:
        index = _corpus_shingle_index(source_corpus, n)
        for uid in sorted(bodies):
            report["matches"].extend(
                find_matches(
                    uid, bodies[uid], index, corpus_kind="source", n=n, min_words=min_words
                )
            )

    if source_selected and not source_corpus:
        report["limitations"].append("no cited-source fulltext available")
    # NFR-14: an empty author corpus is never a clean pass when it is a target.
    if author_selected and not author_corpus:
        report["limitations"].append("author corpus is empty")
        report["result"] = "unknown"
    elif source_selected and not author_selected and not source_corpus:
        report["result"] = "unknown"
    elif report["matches"]:
        report["result"] = "partial"
    return _validated(report)


def _validated(report: dict[str, Any]) -> dict[str, Any]:
    errors = validate("overlap-report", report)
    if errors:
        raise ValueError(f"invalid overlap report: {errors}")
    return report


def findings_from(report: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for m in report["matches"]:
        kind = m.get("corpus_kind", "author")
        if kind == "source":
            reason = (
                f"{m['unit_id']}: {m['overlap_words']} words"
                f" ({m['overlap_ratio']:.0%}) too close to cited source {m['corpus_doc_id']!r}"
            )
            action = (
                "Quote it (quotes + citation + page) or reword in your own words"
                " keeping the citation (writing.source_paraphrase)."
            )
        else:
            reason = (
                f"{m['unit_id']}: {m['overlap_words']} words"
                f" ({m['overlap_ratio']:.0%}) overlap author text {m['corpus_doc_id']!r}"
            )
            action = "Quote and cite the source, or rewrite the fragment."
        findings.append(
            {
                "check_id": "integrity.overlap",
                "severity": m["severity"],
                "reason": reason,
                "location": {
                    "ref": f"unit:{m['unit_id']}",
                    "locator": f"{m['char_start']}-{m['char_end']}",
                },
                "proposed_action": action,
            }
        )
    return findings
