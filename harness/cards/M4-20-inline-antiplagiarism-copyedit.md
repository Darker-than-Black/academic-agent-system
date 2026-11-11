# M4-20 — Inline antiplagiarism + copyedit pass (ADR-026)

> Milestone M4. Modules `integrity.md` (overlap), `review.md`, `claims-text.md`.
> Requirements FR-30, FR-19, ADR-026. Depends on M3-10 (overlap), M4-16
> (cite-binding), M4-18 (writing pack). Base `main`. Implements ADR-026.

## Goal

Catch plagiarism early — during writing, not at the end — and make the writer
produce original scholarly prose that retells sources in the author's own words
and conclusions, while keeping attribution (H6). The aim is to genuinely not
plagiarise, never to evade a detector (N4).

## What this card delivers (slice 1: rule-as-data + prompt; slice 2: overlap vs sources)

- **Rule `writing.source_paraphrase`** in the `writing` pack (integrity, major,
  overridable): text too close to a cited source's wording is quoted (quotes +
  citation + page) or reworded in the writer's own words keeping its citation;
  borrowed wording is never passed off as original.
- **`writer.md` copyedit/rewrite pass** (ADR-026 — the same writer slot, not a
  new role; respects ADR-002 "one writer per object"): paraphrase into original
  prose at narrative depth, keep `[cite:X]` on borrowed specifics, treat the
  similarity gate as a helper, and refuse/ surface any detector-evasion
  instruction (N4). Regenerate the Claude Code subagents.

## Slice 2 — overlap vs cited sources (delivered)

- `integrity/overlap.py`: `load_source_corpus(root)` reads `sources/pagetext/
  <S-id>.jsonl` (gitignored foreign fulltext, runtime-only — the report stores
  source ids + overlap counts, never source text; H8). `run(..., against=...)`
  takes `corpus` (author, self-overlap, as before), `sources` (cited-source
  fulltext), or `both`; matches carry `corpus_kind ∈ {author, source}`; the
  report records `against`. NFR-14 kept: an empty author corpus never yields a
  clean pass when the author corpus is a selected target (result `unknown`).
- `rh overlap --against corpus|sources|both` (`cli/overlap.py`); source findings
  say "too close to cited source … quote or reword keeping the citation".
- Schema: `overlap-report.schema.json` gains optional `against` + match
  `corpus_kind`.

## Not in this card

Inline auto-trigger of `--against both` inside the writing/review flow and
per-unit citation resolution (set `cited=true` when the unit actually cites the
matched source) — follow-up. Similarity thresholds as rule-pack data
(`ua-mon-phd` / `ua-fahove-b`), draft. Optional export of clean material for the
institution's external service (Unicheck / StrikePlagiarism) — the external paid
run stays with the author (H9/H11). No paid detector is integrated; nothing is
rewritten to evade detection (N4).

## Tests

`tests/unit/rules`: the `writing` pack lints clean with the new rule.
`tests/unit/integrity/test_overlap.py`: `load_source_corpus` loads pagetext and
skips empty files; `find_matches` tags `corpus_kind=source` and the finding says
"cited source"; `rh overlap --against sources` with no fulltext → result
`unknown` + limitation. `rh-dev check` green.
