# M3-03 — Unit and chapter critics

> Milestone M3a. Module `review.md`. Requirements FR-14, FR-49.
> Tests T06 (H threshold), T05 (review), T53 (critics baseline).
> Depends on M3-02. **Stacked on `m3/M3-02-review-framework`.**

## Goal

Fresh-context unit and chapter critics that emit support verdicts, with the
numbers a claim takes from a source checked against that claim's own excerpts
(ADR-009 p.4).

## What this card delivers

- **`review/numbers.py`** (core, LLM-free, deterministic) — the numbers-from-
  sources aid: a number stated in an external claim that appears in none of that
  claim's cited excerpts is `review.number_not_in_excerpt` (major). Numbers are
  compared as normalized tokens (decimal comma → dot, trailing `%` kept), never
  as substrings, so `7` never matches `17` and `42` never matches `42%` — which
  is exactly what surfaces a percent/percentage-point slip (D7) or a wrong-table
  figure (D8). It only ever compares a claim's numbers to that claim's excerpts.
- **`rh review numbers --unit U`** — runs the check over a unit's external
  claims; `partial` when anything is flagged.
- **Critic prompts** (`harness/prompts/unit_critic.md`, `chapter_critic.md`),
  regenerated into `harness/host/claude-code/agents/{unit-critic,chapter-critic}.md`
  via `rh-dev host generate claude-code` (never hand-edited):
  - unit critic now records `evidence_refs`, `access_level`, `confidence`
    (the M3-02 verdict contract) and applies the numbers discipline — a
    percent/pp or wrong-table number is `contradicted`, not `supported`.
  - chapter critic now flags logic breaks across subsections and chapter
    conclusions ungrounded in the subsections (D17), and cross-unit number
    agreement.

## Not in this card / needs a run

- The critic baselines **T05 / T06 / T53** are flagship eval runs (like the M2
  F4-W baseline): the author triggers them; the H-threshold (recall of critical
  seeded defects ≥ 0.85) is checked at the M3 gate (M3-24), not here.
- Wiring `prepare` to a `review-request` with `snapshot_id`/`fresh_context`/
  `engine` and the `unit|chapter|integration` level rework lands with M3-04
  (integration critic + fulltext CLI) where the snapshot binding matters.

## Tests

`tests/unit/review/test_numbers.py`: token normalization, missing/present
number, token-boundary (no substring match), and skips (no excerpt / no number /
internal claim). Full `rh-dev` gate green (import guard, i18n parity, host-gen
in sync).
