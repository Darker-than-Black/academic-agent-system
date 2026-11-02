# M3-23 — Rule packs for integrity and venue

> Milestone M3a. Module `integrity.md`. Requirements FR-27, FR-30, FR-37.
> Tests T31, T39. Depends on M1-08. Base `main`.

## Goal

Move overlap thresholds, AI-statement requirements and venue rules out of code
and into rule-pack data, checked against primary texts.

## What this card delivers

- **`rulepacks/ua-mon-phd/`** (layer 6, regulator; draft): rules
  `integrity.overlap_uncited` (blocker — self-overlap blocks thesis counting),
  `process.ai_statement_required` (major), `integrity.primary_sources` (major);
  plus **`overlap.yaml`** data (shingle 8, min fragment 25 words, high ratio
  0.30, uncited severity blocker — the thresholds M3-10 defaulted to in code).
- **`rulepacks/scopus-indexed/`** (layer 5, venue class; draft): rule
  `integrity.venue_status` (blocker; `compare: required`, `value: included`).
- **`rulepacks/ua-fahove-b/rules/venue.yaml`**: `integrity.venue_status` for the
  Ukrainian Перелік category «Б» (major — `[Н?]` capped at major), valid on the
  Перелік window (2026-06-01…2029-06-01, наказ МОН № 928).
- Every rule carries a primary `source` and lints clean against `rule` /
  `rulepack` schemas.

## Not in this card

Wiring the thresholds and `rule_refs` into the overlap (M3-10) and venue (M3-12)
checks — those modules read code defaults today; the follow-up reads
`ua-mon-phd/overlap.yaml` and the venue packs once this is merged (and in verified
export, M3-15). The AI-statement template text is M3-11. Values stay **draft**
until the author confirms them against МОН № 928 and the target venue.

## Tests

`tests/unit/rules/test_loader.py`: the three packs lint clean, the ua-mon-phd
overlap thresholds load, and the Scopus venue rule requires `included` at blocker
severity. Full `rh-dev` gate green.
