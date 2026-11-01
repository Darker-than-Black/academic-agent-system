# M3-10 — Overlap check

> Milestone M3a. Module `integrity.md`. Requirements FR-30, NFR-14.
> Test T31. Base `main` (independent).

## Goal

Deterministic overlap of the current text with the author's own corpus
(`_author/corpus/`), Cyrillic- and Latin-aware, so the author can see and cite or
rewrite reused fragments before anything leaves the harness.

## What this card delivers

- **`integrity/overlap.py`** (core, LLM-free):
  - word-token normalization (casefold, Unicode `\w` so Cyrillic and Latin both
    tokenize; punctuation and underscores dropped), with char spans kept.
  - `load_corpus` reads `_author/corpus/**/*.{md,txt}` keyed by relative path.
  - `find_matches` — maximal contiguous runs of corpus-matching shingles
    (default size 8) of ≥ `min_fragment_words` (default 20); each match records
    char span, `corpus_doc_id`, `overlap_words`, `overlap_ratio`, `cited`
    (false; see limitations) and severity (major ≥ 30 % ratio, else minor).
  - `run` builds the report; **an empty corpus gives `result: unknown`** (never a
    clean pass, NFR-14).
- **`schemas/overlap-report.schema.json`** — report + match records
  (integrity.md data contract); reports written to
  `integrity/overlap/<run-id>.json` validate against it.
- **`rh overlap [--unit U]`** — runs the check against the workspace author
  corpus, writes the report, returns matches as findings.

## Deferred

- Rule-pack thresholds and severities (`ua-mon-phd`, `ua-fahove-b`) — the packs
  are written in M3-23; defaults here (shingle 8, min 20 words, 30 % ratio) are
  conservative stand-ins, and `rule_refs` is empty until then.
- Citation detection (`cited` stays false; stated in `limitations`) and
  `snapshot_id` binding — later integrity/export cards. Thesis-level use is M4.

## Tests

`tests/unit/integrity/test_overlap.py`: Cyrillic tokenization/shingles, long
overlap matched, short overlap below threshold, case-insensitive match, corpus
loading, empty-corpus → unknown. overlap-report schema examples (empty→unknown,
with-match, two invalid). Full `rh-dev` gate green.
