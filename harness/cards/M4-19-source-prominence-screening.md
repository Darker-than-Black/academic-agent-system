# M4-19 — Source-selection prominence (advisory screening signal, ADR-025)

> Milestone M4. Modules `research-lab.md`. Requirements ADR-025, FR-20, FR-56.
> Depends on M2 (search/screen), ADR-016 (adapters). Base `main`.
> Addresses the second read-through feedback (item 3). Implements ADR-025.

## Goal

Give source selection an explicit validation signal — the prominence of the
source and its author — without letting it override relevance or reject
mindlessly, and without ever surfacing the numbers in the manuscript (H6/H7).

## What this card delivers (first slice: rule-as-data + prompt + protocol doc)

- **New advisory rule pack `rulepacks/screening/`** (layer 2, no `applies_when`,
  `status: draft`): `screening.source_prominence` (process, minor, overridable).
  At `rh screen`, record source/author prominence (works count, citations,
  h-index, venue) as advisory data — one signal among others, never the sole
  criterion; a low-/unknown-prominence include needs a stated reason; signals
  stay in the screening log, never in the manuscript.
- **`researcher.md`** — the screen step records prominence as advisory data,
  subordinate to the existing "citation count is not the only quality signal"
  rule; `unknown` is never guessed (H6/H7).
- **Protocols** `literature-narrative` / `conceptual` — the optional advisory
  `selection_validation` signal documented (not required, not a G2 field).

## Not in this card

Executable wiring: OpenAlex (`works_count`, `cited_by_count`, authorships) and
Semantic Scholar (`hIndex`, `paperCount`) — keyless, free, so **H9 is not
engaged** — fetched at `rh screen` and written to `lab/screening.jsonl`; the
screening report flags an include that has no reason at low/unknown prominence.
Prominence thresholds ("what counts as low") land as rule-pack data, draft, for
the author to confirm. No manuscript surfacing, ever (ADR-025). Nothing invented
(H6/H7).

## Tests

`tests/unit/rules`: the `screening` pack lints clean and resolves into the stack
(no `applies_when`). `rh-dev check` green.
