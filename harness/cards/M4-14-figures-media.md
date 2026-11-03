# M4-14 — Figures and media in articles

> Milestone M4. Modules `docx.md`, `analysis-sandbox.md`, `claims-text.md`.
> Requirements FR-43, ADR-009. Tests new. Depends on M3-20 (figures from rows),
> M2-12 (export). Base `main`. Addresses test-run feedback item 3.

## Goal

Let an article carry figures / tables / media with provenance, and render them in
the manuscript and the .docx. The test-run article had none; an empirical article
(per ADR-023 `article_type`) must be able to show a visual of its data/experiment.

## What this card delivers

- **Figure model** — a figure record: id, caption, kind (chart | image | table),
  **source/provenance** (derived from `runs`/`rows` per M3-20/ADR-009, or an
  author-provided asset with an adoption/asset record), `alt` text, and a stable
  anchor.
- **In-text placement** — reference a figure from a unit body (e.g.
  `{{fig:F-0001}}`), resolved in assembly; integration check that every figure is
  referenced and every reference resolves (mirrors the cross-ref check).
- **Export** — figures embedded in `manuscript.md` and the .docx (image/table);
  captions numbered deterministically.
- **Tie to ADR-023** — for `article_type: empirical`, readiness expects ≥ 1 result
  figure/table; its absence is part of the substance report, not invented.
- **No invention (H6).** Figures come from real `rows`/`runs` or real author
  assets; the harness never fabricates a chart from nonexistent data.

## Not in this card

A full charting engine / styling system — reuse M3-20 (figures from rows) for
chart generation; this card wires figures into the article model, placement, and
export. Author-supplied binary assets follow the asset/rights rules (M3-12); no
foreign-rights media in git (H8).

## Tests

`tests/integration/test_docx.py` (or figures test): a unit with `{{fig:F-0001}}`
renders the figure + numbered caption in md and .docx; an unreferenced figure and
an unresolved `{{fig:...}}` each produce a finding. Full `rh-dev` gate green.
