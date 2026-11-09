# M4-18 — Writing-quality rules (presentation + narrative substance, ADR-024)

> Milestone M4. Modules `review.md`, `claims-text.md`. Requirements ADR-024,
> FR-09. Depends on M3-03 (critics), M4-15 (substance). Base `main`.
> Addresses the second read-through feedback (items 1, 2, 4, 5, 6, 7).
> Implements ADR-024. Source-selection prominence (item 3) is M4-19 (ADR-025).

## Goal

Make a drafted publication read as a scientific narrative, not a summary, and
keep presentation conventions the author asked for — without the harness
inventing content (H6) or editing the author's text unasked (H13). Presentation
rules warn, never hard-block (ADR-022); narrative depth is a substance warning
(ADR-023).

## What this card delivers (first slice: rules-as-data + prompts)

- **New general rule pack `rulepacks/writing/`** (layer 1, no `applies_when` —
  always on; `status: draft`). A venue/type pack may override a threshold by the
  same key at a higher layer. Rules:
  - `writing.abstract_no_conclusions` (major) — abstract = intro + relevance
    only; no results/conclusions.
  - `writing.citations_in_references` (minor) — full entries only in References;
    body uses in-text refs (max a title); no repeated full source listings.
  - `writing.no_premature_conclusions` (major) — final conclusions only in the
    Conclusions unit.
  - `writing.narrative_depth` (major) — body narrates hypotheses, how tested,
    path to each conclusion; not a bare results summary.
  - `writing.section_min_substance` (minor, `min: 3` paragraphs) — group tiny
    1–2 paragraph sections.
  - `writing.figure_requires_explanation` (major) — each figure has text: how
    obtained + what it shows.
- **Prompts** updated to enforce these: `writer.md` (draft with narrative depth
  and the placement/citation/figure rules), `chapter_critic.md` (premature
  conclusions, tiny sections, repeated sources, summary-not-narrative),
  `integration_critic.md` (abstract scope, premature conclusions, unexplained
  figures). Regenerate the Claude Code subagents afterward
  (`uv run rh-dev host generate claude-code`).

## Not in this card

Deterministic proxies (paragraph count per section; conclusion/limitation
markers in abstract and body; a figure reference with no adjacent explanation; a
repeated full reference in the body) wired into `rh review integration` /
`substance/report.py` — next slice, per ADR-024, mirroring the
`substance.analysis_free_ratio` checker. Semantic narrative depth stays a critic
judgement. No change to honesty gates. No text is rewritten (H13). Item 3
(source-selection prominence) is M4-19.

## Tests

`tests/`: the `writing` pack loads and schema-validates; it resolves into the
stack for an article and for a thesis (no `applies_when`); a venue pack overriding
`writing.section_min_substance` wins by layer. `rh-dev check` green.
