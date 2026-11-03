# M4-16 — Citation binding + bibliography rendering

> Milestone M4. Modules `claims-text.md`, `docx.md`, `sources-library.md`.
> Requirements FR-12, FR-43. Tests new, T43 (regression). Depends on M2-01
> (sources), M2-07 (drafting), M4-12 (format). Base `main`. Addresses test-run
> critical item 1 (no bibliography) and the `[N, с. X]` in-text requirement.

## Problem

The reference builder (`export_docx/references.py`) collects cited keys from
`@key` / `[[cite:key]]` markers in unit bodies, resolves them against the source
registry, and emits the bibliography. The drafting step instead produced **prose
citations** ("(Meng et al., 2024)") with **no machine-readable markers**, so
`cited_keys` is empty → `references.bib` is empty and "Список використаних джерел"
has no entries. In-text references also cannot be rendered as the venue's
`[N, с. X]` or verified against claims.

## What this card delivers

- **Cite markers at drafting.** The writer emits `[[cite:<bib_key>]]` (optionally
  with a page: `[[cite:<key>|с.25]]`) bound to a registry record, instead of (or
  alongside) prose author-year. Each material claim's source is cited at the
  sentence that asserts it.
- **Registry binding.** Every cite marker must resolve to a non-`not_found`
  record with a `bib_key`; an unresolved key is `export.cite_unresolved` (blocker,
  already implemented) — never fabricated (H6).
- **In-text rendering.** On export, markers render per the venue preset: numeric
  `[N]` or `[N, с. X]` (ADR-022 preset), numbered in order of first appearance,
  matching the bibliography order.
- **Bibliography.** `references.bib` + the rendered "Список використаних джерел"
  are built from the resolved cited records (existing builder), now non-empty.
- **Coverage.** A check that every material claim with external evidence has at
  least one in-text cite, and every cited key appears in the bibliography.

## Not in this card

Enforcing ДСТУ punctuation inside each reference entry (that is the CSL preset,
M3-13/ADR-022). Back-filling markers into already-drafted prose for A-2026-001 is
a one-off rework, not part of the mechanism. Page-accurate locators depend on the
excerpt locator model (M2-05), reused here, not redefined.

## Tests

`tests/integration/`: a unit body with `[[cite:key]]` for a registry record →
non-empty `references.bib` + in-text `[N]`/`[N, с.X]` in the export; a claim with
external evidence but no in-text cite → finding; an unresolved key → blocker
(regression T43). Full `rh-dev` gate green.
