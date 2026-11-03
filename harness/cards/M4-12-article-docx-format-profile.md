# M4-12 — Article .docx formatting profile (ua-fahove-b)

> Milestone M4. Modules `docx.md`, `integrity.md`. Requirements FR-12, FR-43.
> Tests T46 (regression), new. Depends on M2-12 (export), M3-23 (venue/style packs).
> Base `main`. Addresses test-run feedback item 1.

## Goal

Produce article .docx that meets the Ukrainian cat. «Б» general formatting
requirements, instead of pandoc defaults. From the author's venue requirements
screenshot: A4, **≤ 20 pages**, **Times New Roman 14 pt**, **1.5 line spacing**,
**first-line indent 1.25 cm** (set by paragraph style, not spaces/Tab), **margins
2 cm** all sides, **page numbers bottom-centre**.

## What this card delivers

- **`rulepacks/ua-fahove-b/reference.docx`** — a reference document encoding the
  styles above (Normal = TNR 14 / 1.5 / indent 1.25 cm; margins 2 cm; footer page
  number centred; heading styles). Pandoc renders against it.
- **`export_docx`** — use this reference.docx for article exports (draft and
  verified); select it as a preset per ADR-022 (presentation layer).
- **`rulepacks/ua-fahove-b/rules/format.yaml`** (data, draft) — deterministic
  checks that produce findings, not blockers for draft (ADR-022): `format.volume`
  (> 20 A4 pages → major), `format.citation_style` (in-text numeric refs present
  where stats/tables/quotes appear → see note), `format.self_citation` /
  `format.outdated_sources` (advisory). Values stay **draft** until the author
  confirms against the venue guidelines.
- A deterministic **page-count estimate** for `format.volume` (chars → A4 pages at
  the profile; report, not a hard block for draft).

## Not in this card

Enforcing in-text bracketed references `[N, с. X]` on every statistic/table/quote
is a semantic check — scoped as a follow-up with the claims/location model (it
needs claim↔sentence binding and page locators). This card lands the reference.docx
+ volume/advisory findings. The bibliography STYLE (ДСТУ CSL preset) is M3-13 /
ADR-022, not re-litigated here. Thesis format (наказ МОН № 40) stays M4-07.

## Tests

`tests/integration/test_docx.py` (or export test): an article export uses
reference.docx (assert core style: font TNR, size 14, 1.5 spacing, 2 cm margins
read back from the produced .docx); `format.volume` fires major above the page
threshold. Full `rh-dev` gate green.
