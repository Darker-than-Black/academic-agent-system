# M4-25 — Overlap similarity threshold as rule-pack data (ADR-026)

> Milestone M4. Module `integrity.md` (overlap), rulepacks `writing`,
> `ua-mon-phd`, `ua-fahove-b`. Requirements FR-27, FR-30, ADR-026. Depends on
> M4-20/21/24 and the rule resolver (M3-23). Base `main`.

## Why

The major-vs-minor overlap threshold was the hardcoded constant `HIGH_RATIO =
0.30` in `integrity/overlap.py`. A МОН dissertation and a fahova-B article must
hold different strictness, and that belongs in rule-pack data the author can see
and a regulator can tighten — not in code.

## What this card delivers

- **Rule `integrity.overlap_high_ratio`** (kind `integrity`, `compare: max`):
  the fraction of a unit an overlap fragment must reach to be a `major` finding
  (below it, `minor`).
  - `writing` pack (always-on, layer 1): default `"0.30"`.
  - `ua-fahove-b` (article, layer 3): `"0.25"`.
  - `ua-mon-phd` (thesis, layer 6): `"0.15"` (strictest).
  `compare: max` means `_combine` takes the minimum across applicable packs, so
  the strictest value wins; with no regulator pack the default 0.30 stands.
- **`overlap._high_ratio(root)`** resolves the effective value from the object's
  rule stack (`rules.service.resolve_object`, `write=False`), falling back to
  `HIGH_RATIO` on any failure (no object, no rule, unparseable). `find_matches`
  takes a `high_ratio` parameter; `run` threads the resolved value through and
  records it in `method.high_ratio` and the rule id in `rule_refs`. The review
  flow (`rh review fulltext`, M4-21) inherits it automatically since it calls
  `run`.
- Schema: `overlap-report.schema.json` `method` gains optional `high_ratio`.

## Not in this card

Only the severity ratio is pack-governed. The detection floor (`min_fragment_words`,
`shingle_size`) stays a module constant — changing it alters what is detected at
all, a larger behaviour change left as a follow-up. No change to the separate
`integrity.overlap_uncited` thesis rule (self-plagiarism counting, M3-23).

## Tests

`tests/unit/integrity/test_overlap.py`: `find_matches` severity flips with the
`high_ratio` parameter; `_high_ratio` falls back to the default without an object
and resolves 0.25 for an article object, 0.15 for a thesis object; `run` records
the resolved `high_ratio` in the report method. `rh-dev check` green (pack lint,
schema, i18n, yaml guards all pass).
