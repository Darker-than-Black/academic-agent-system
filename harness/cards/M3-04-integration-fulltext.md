# M3-04 — Integration critic + full-text CLI checks

> Milestone M3a. Module `review.md`. Requirements FR-22 (integration part), FR-49.
> Tests T53 (CLI), T22. Depends on M3-02. **Stacked on `m3/M3-03` (shared
> cli/review.py).**

## Goal

`rh review fulltext`: deterministic document-wide checks over the whole object's
current unit bodies, feeding the integration review (map.md + summaries + these
results).

## What this card delivers

- **`review/fulltext.py`** (core, LLM-free):
  - `fulltext.crossref` (blocker) — every `{{ref:U-…}}` resolves to a unit.
  - `fulltext.cite_keys` (blocker) — every cite key in the text (`@key` or
    `[[cite:key]]`) exists in `sources/registry.jsonl`. The reverse direction
    (a source never cited) is rule-pack governed → M3-23.
  - `fulltext.repeated_fragment` (major) — a normalized word shingle of ≥ 40
    words occurring in two different units (D16); reported once per fragment,
    same-unit repeats ignored.
  - glossary consistency — delegated to the glossary module
    (spec's `fulltext.term_glossary`; the glossary check owns its finding ids).
- **`rh review fulltext`** — runs all of the above; `blocked` (exit 3) when any
  blocker, else `partial` when findings, else `ok`.

## Deferred

- `fulltext.numbering` (needs figure/table numbering infra) and `fulltext.volume`
  (needs the thesis volume counter, thesis.md) → later M3a / M4.
- The semantic integration critic (abstract↔results↔conclusions D13,
  cross-chapter D15) stays the `integration-critic` subagent; its baseline is a
  flagship eval run (T22) at the M3 gate. The deterministic `rh review
  integration` (v0) is unchanged.
- `review-request`/snapshot binding and the level rework remain as noted in M3-02.

## Tests

`tests/unit/review/test_fulltext.py`: crossref resolved/unresolved, cite key
unknown + bracket syntax, repeated fragment across units, short-overlap and
same-unit negatives. Full `rh-dev` gate green.
