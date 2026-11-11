# M4-21 — Auto-run cited-source overlap in the review flow (ADR-026)

> Milestone M4. Modules `review.md` (fulltext), `integrity.md` (overlap).
> Requirements FR-30, FR-49, ADR-026. Depends on M4-20 (overlap vs sources).
> Base `main`. Follow-up to M4-20 ("Not in this card": inline auto-trigger).

## Goal

Catch copying from a cited source during the normal review flow, not only when
the author remembers to run `rh overlap --against sources` by hand. The aim is
to genuinely not plagiarise, never to evade a detector (N4).

## What this card delivers

- **`review.fulltext.check_source_overlap(root)`** — `rh review fulltext` now
  auto-runs `overlap.run(root, against="sources")` and turns each match into a
  finding (`integrity.overlap`, major/minor: a unit body too close to a cited
  source's fulltext → quote or reword keeping the citation). It needs only the
  object root (`sources/pagetext/<S>.jsonl`, gitignored, runtime-only — H8); no
  workspace/author-corpus resolution, so it fits the deterministic doc-wide
  runner that already feeds integration review.
- **H7 — absence is not a pass.** When no cited-source fulltext is available the
  overlap result is `unknown`; we surface one `info` finding
  ("cited-source overlap not checked: no source fulltext available") instead of
  letting the silence read as clean.
- Severity stays major/minor/info — never a blocker, so it warns and guides
  (ADR-022 spirit) without hard-blocking export; the integrity rule
  `writing.source_paraphrase` remains the semantic backstop.
- `integration_critic.md` prompt notes the auto-run overlap finding.

## Not in this card

Author-corpus (self-overlap) is left to the explicit `rh overlap` /
`--against both`; wiring it into the review flow needs the workspace root, which
`review.fulltext` (core) does not resolve. Per-unit citation resolution (set
`cited=true` when the unit actually cites the matched source) and similarity
thresholds as rule-pack data (`ua-mon-phd` / `ua-fahove-b`) stay follow-ups.

## Tests

`tests/integration/test_fulltext_run.py`: `rh review fulltext` emits an `info`
`integrity.overlap` finding when no source fulltext is present; emits a
major/minor "cited source" finding when a unit body copies a cited source's
pagetext. Existing fulltext tests filter by `check_id`, so the added findings
do not disturb them. `rh-dev check` green.
