# M3-13 — Style and typical-errors profiles

> Milestone M3a. Module `integrity.md`. Requirements FR-19, FR-19a, FR-51.
> Tests T19, T47 (baseline), T56. Base `main`.

## Goal

Help the author avoid his own typical errors and keep a consistent voice, while
the harness **never** changes numbers/citations/qualifiers during stylization
and **never** introduces an error into any version or export.

## What this card delivers

- **`rulepacks/core/errors-catalog.yaml`** (rule-pack data, uk + en): categories
  (voice/person, calques/bureaucratese, terminology, argumentation, formatting,
  structure); deterministic calque→preferred list and voice markers.
- **`integrity/style.py`**: `invariant_check(before, after)` →
  `integrity.style_invariants` **blocker** when numbers, citation markers,
  qualifiers or limitation markers differ (T19, FR-19a — invariants hold 100 %);
  `build_profile` → deterministic features (sentence length, dominant voice,
  connectives) written to a style profile.
- **`integrity/errors.py`**: `check_text` → `integrity.chosen_error` (major) /
  `integrity.error` (minor) for listed calques and voice/person mixing — **never
  edits the text** (T56); `choose` persists the author's categories.
- **`rh style profile build --lang L`**; **`rh errors profile choose
  --category … [--voice]`** / **`rh errors check --unit U`**.
- Schemas `style-profile` + `errors-profile` with examples; i18n en+uk.

## Deviations / deferrals

- The catalogue lives at `rulepacks/core/errors-catalog.yaml`, **not** under
  `core/rules/` as the spec text suggests: files in `rules/` are loaded by the
  rule resolver (which requires a `key`), so the catalogue sits beside `pack.yaml`.
- Deferred: `rh style profile propose` / `accept` (proposals from the author's
  edits, applied only after the author accepts in a human channel); semantic
  error categories (terminology/argumentation/…) and the `.docx`-edit priority
  (M3-09); the T47/N4 "hide AI" refusal baseline (ties into M3-11).

## Tests

`test_style.py` (invariants preserved on reword; number/citation/qualifier change
blocks; profile voice + features) and `test_errors.py` (calque chosen vs
unchosen severity, voice mixing, clean text, input never mutated, choose +
unknown category, catalogue loads). Schema examples pass. Full `rh-dev` gate green.
