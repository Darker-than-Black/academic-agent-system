# M4-24 — Per-unit citation resolution for source overlap (ADR-026)

> Milestone M4. Module `integrity.md` (overlap), `review.md` (fulltext).
> Requirements FR-30, ADR-026. Depends on M4-20/M4-21 (overlap vs sources in the
> review flow). Base `main`. Closes the standing `cited=false` limitation.

## Why

`rh overlap --against sources` and the auto-run in `rh review fulltext` (M4-21)
flagged every unit fragment that overlaps a source's full text as major/minor,
whether or not the unit actually cites that source. Properly quoted-and-cited
material therefore shouted as loudly as an undisclosed copy, and the report
carried a blanket limitation `citation detection not applied (cited=false)`.
That noise undermines the check the author just asked for. This card resolves,
per unit, whether an overlapping source is cited, and tunes the finding
accordingly.

## What this card delivers

- **`overlap._resolve_cited`** sets `cited` on each source-kind match. A match's
  `corpus_doc_id` is the source id (the `sources/pagetext/<S>.jsonl` stem); the
  unit cites by bib_key, so a match is `cited` when the unit body cites the
  source id or its bib_key (`sources.registry` maps id→bib_key; cite markers
  `@key` / `[[cite:key]]` parsed with the same regex the fulltext checks use).
  Author-corpus (self-overlap) matches are left untouched — citation does not
  apply to one's own prior text.
- **`findings_from`** now distinguishes three cases: a **cited** source overlap
  is `info` ("overlap cited source S-x … make it a marked quotation or reword —
  a citation alone does not license borrowed wording"); an **uncited** source
  overlap keeps major/minor ("too close to source S-x, not cited here — quote
  and cite, or reword"); author overlap is unchanged. A citation never clears
  the finding entirely (H6) — it downgrades the alarm, it does not license copy.
- The blanket `cited=false` limitation is gone; the report instead notes
  `author-corpus overlap is not citation-resolved` only when an author corpus is
  actually in scope.

## Not in this card

Quotation-vs-copy discrimination (is the cited overlap inside quote marks with a
page?) stays with the semantic unit critic (`writing.source_paraphrase`, M4-22);
the deterministic check cannot see quotation intent. Similarity thresholds as
rule-pack data (`ua-mon-phd` / `ua-fahove-b`) remain a follow-up.

## Tests

`tests/unit/integrity/test_overlap.py`: an uncited source match reports
"not cited here"; a match with `cited=True` is `info` and says "cited source".
`tests/integration/test_fulltext_run.py`: a unit that copies S-0001 without
citing it is major/minor "not cited here"; the same overlap with `[[cite:meng2024]]`
in the unit is downgraded to `info`. `rh-dev check` green.
