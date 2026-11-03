# M4-17 — Review methodology: reproducible corpus (PRISMA-style)

> Milestone M4. Modules `research-lab.md`, `sources-library.md`, `docx.md`.
> Requirements FR-09, ADR-023. Tests new. Depends on M2-01 (sources), M4-15
> (article_type / readiness). Base `main`. Addresses test-run critical item 2 and
> pasted item 1 (corpus not reproducible).

## Problem

For a `review` article the methods named only the four fulltext sources; the other
five of nine were not identified, and the manuscript gave no selection criteria,
search dates, queries, counts found/screened/excluded, or exclusion reasons. A
reader/journal cannot reproduce how the corpus was formed.

## What this card delivers

- **Search log** — a structured, deterministic record of the corpus formation:
  databases/sources queried, exact queries, dates, counts found, screened,
  included, excluded + exclusion reasons (a PRISMA-style flow the author fills /
  the search step records). No invented numbers (H6); missing → `unknown` (H7).
- **Included-studies table** — every source in the corpus identified (all nine,
  not just fulltext ones): id, full citation, access level, role in synthesis;
  rendered into methods on export.
- **Selection criteria** — inclusion/exclusion criteria in operational form, as a
  structured field, surfaced in methods.
- **Readiness tie-in (M4-15).** For `article_type: review`, readiness requires:
  all corpus sources identified (no bare metadata-only unknowns among material
  sources), a search log present, and selection criteria stated. Gaps are listed
  as "what to provide", never filled in.
- **Flow diagram** — optional PRISMA flow figure via the figures model (M4-14).

## Not in this card

Automating the literature search itself (fetching records from databases) — the
search adapters are M2-01/M3; this card is the methodology record + its checks +
rendering. Semantic judgement of synthesis depth is M4-15 / integration critic.

## Tests

`tests/integration/`: a review object missing the search log / with
unidentified corpus sources fails the M4-17 readiness checks with a listed
deficit; a complete corpus + search log passes and renders the included-studies
table in methods. Full `rh-dev` gate green.
