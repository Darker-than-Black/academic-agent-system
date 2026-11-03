# M4-13 — Source language / jurisdiction check (no ru/by sources)

> Milestone M4. Modules `sources-library.md`, `integrity.md`. Requirements FR-27,
> FR-37. Tests new. Depends on M2-01 (sources), M3-23 (rulepacks). Base `main`.
> Addresses test-run feedback item 2.

## Goal

Flag sources that Ukrainian cat. «Б» guidelines forbid citing. From the author's
screenshot: do **not** cite or include in the bibliography sources **published in
Russian in any country**, nor sources in other languages **published on the
territory of russia or belarus**.

## What this card delivers

- **Source metadata** — ensure each source record can carry `language` and
  `publication_country` (ISO code) / publisher country, resolved via `source
  lookup` (Crossref/metadata) where available; missing → `unknown` (H7), never
  guessed.
- **`rulepacks/ua-fahove-b/rules/sources.yaml`** (data, draft):
  - `integrity.source_language_forbidden` — language == `ru` → **blocker** (any
    country).
  - `integrity.source_jurisdiction_forbidden` — publication/publisher country ∈
    {RU, BY} → **blocker**.
  - `integrity.source_origin_unknown` — language or country `unknown` for a cited
    source → **major** (author must resolve; H7 does not pass a required check).
- **Deterministic check** over cited sources + bibliography entries; emits findings
  with the offending source id and the rule ref. Runs in validation and before
  export.
- Findings carry `next_actions` telling the author to drop/replace the source or
  resolve its metadata.

## Not in this card

Auto-detecting language from title/abstract heuristics beyond the metadata field
(a classifier) — out of scope; we use resolved metadata and `unknown` otherwise.
Removing a flagged source from the manuscript is the author's edit (H13), not
automatic. Thresholds/severities stay **draft** until the author confirms them
against the venue rules.

## Tests

`tests/unit/rules/test_loader.py` + a sources integration test: a `ru`-language
source → blocker; a source with country RU/BY → blocker; an `unknown`-origin cited
source → major; a clean EN/UA source → no finding. Full `rh-dev` gate green.
