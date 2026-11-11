# M4-27 — Overlap detection knobs as pack data + inline gate in the writer loop (ADR-026)

> Milestone M4. Module `integrity.md` (overlap), `claims-text.md` (writer),
> rulepacks `writing` / `ua-mon-phd` / `ua-fahove-b`. Requirements FR-27, FR-30,
> ADR-026. Depends on M4-25 (`integrity.overlap_high_ratio`). Base
> `feat/m4-25-overlap-threshold-rulepack` (stacked). Finishes the antiplagiarism
> follow-ups in one card (author asked not to split).

## What this card delivers

### A. Detection knobs as rule-pack data

M4-25 moved the major/minor **ratio** into `integrity.overlap_high_ratio`. This
card does the same for the two remaining hardcoded knobs:

- **`integrity.overlap_min_words`** — the shortest contiguous overlap reported.
  writing 20, ua-fahove-b 18, ua-mon-phd 15.
- **`integrity.overlap_shingle_size`** — the matching shingle length. writing 8,
  ua-fahove-b 7, ua-mon-phd 6.

All `kind: integrity, compare: max` (strictest, i.e. smallest, applicable value
wins — a dissertation is more sensitive than an article than the default).
`overlap._high_ratio` is generalised to **`overlap._thresholds(root)`**, which
resolves all three from the object's rule stack (`resolve_object`, `write=False`)
and falls back to the module constants on any failure. `run` resolves them once
and threads them through; `run`'s `n` / `min_words` become `None`-defaulted
overrides (callers that pass nothing get the pack-resolved values). `method` in
the report carries `shingle_size`, `min_fragment_words`, `high_ratio`; `rule_refs`
names the rules that set them. The review flow (`rh review fulltext`) and the CLI
inherit it, since both call `run`.

### B. Inline gate in the writer loop

`writer.md` now makes the similarity gate an explicit step: after the draft or
copyedit write, run `rh overlap --against both --unit <U>` (author corpus +
cited-source full text), treat each finding (uncited source overlap → quote-cite
or reword; cited source → marked quotation or reword; self-overlap → rewrite;
`info` → note, not a pass), then rewrite and re-run until clean. It is a helper,
not a hard block, but the writer clears it rather than ignores it. Subagents
regenerated.

## Not in this card

`normalization` stays fixed (it is the tokeniser, not a sensitivity knob). No new
command — the inline gate reuses `rh overlap`. The external-detector boundary is
ADR-026 (M4-26 doc).

## Tests

`tests/unit/integrity/test_overlap.py`: `_thresholds` falls back to the three
constants without an object and resolves 0.25/18/7 (article) and 0.15/15/6
(thesis); `run`'s report method carries the resolved `high_ratio`,
`min_fragment_words`, `shingle_size`. Existing overlap/fulltext/fixtures tests
stay green. `rh-dev check` green (pack lint, schema, i18n, yaml guards).
