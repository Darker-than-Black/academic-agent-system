# M4-11 — Presentation separate from integrity; venue informational

> Milestone M4. Modules `integrity.md`, `docx.md`, `intake-rules.md`.
> Implements ADR-022. Requirements FR-12 (verified). Tests T46, T39, new.
> Depends on M3-15 (verified export), M3-12 (venue), M3-13 (style errors). Base `main`.

## Goal

Stop treating bibliography style and venue status as integrity gates. Per
ADR-022: verified export must refuse only on evidence-traceability blockers
(claims↔evidence, quote_check, overlap, G3). Bibliography style/appearance becomes
a presentation layer; venue becomes informational metadata from intake with no
status check or gate.

## What this card delivers

- **`integrity/verified.py: check_conditions`** — remove `venue.status_findings`
  from the verified conditions. `export.style_unvalidated` is no longer a blocker
  condition; it is emitted (if at all) as an optional warning that does NOT enter
  the refusal set.
- **`cli/export.py` (`_verified`)** — refuse only when there is at least one
  **blocker**-severity finding, not on any finding
  (`if any(f["severity"] == "blocker" for f in findings)`). Non-blocker
  presentation/venue findings are returned as warnings alongside a produced
  bundle (status `partial`, exit 0), never a `blocked` refusal.
- **`integrity/venue.py`** — `status_findings` demoted to an informational note
  (or dropped from verified entirely). `rh venue check` stays as an optional
  author tool; it is no longer a precondition of verified export. The
  date-stamp / Перелік-currency check is removed (author owns that risk, ADR-022).
- **Intake / object metadata** — venue identity (title / URL) captured at intake
  and stored as object metadata; no `venue check` required downstream.
- **`export_docx`** — bibliography style is a selectable **preset**; draft and
  verified both render freely with any preset and can be re-rendered without a new
  integrity pass. The clean-room ДСТУ 8302:2015 CSL remains one preset; an
  unvalidated style yields at most a warning, never a block.
- **H-rule docs** (`AGENTS.md`, `spec-v0.2/00-README.md`, `05-agents.md`) — note
  that venue is informational and bibliography formatting is not an integrity gate.

## Not in this card

The bibliography-format questionnaire UX at Word-generation time (ADR-022 §4) —
the interactive prompt is a thin follow-up once presets exist; this card delivers
the preset mechanism and the gate removal. No change to the traceability gates
(claims, quote_check, overlap, G3) — those stay exactly as they are. Scraping a
venue's author-guidelines into a preset (data only, H10/H12) is a separate card.

## Tests

- `tests/integration/test_export.py` (or verified export test): a snapshot whose
  only open findings are `export.style_unvalidated` and/or an unknown venue now
  **produces** a verified bundle (status partial + warnings), and is refused only
  when a real traceability blocker (unsupported material claim, invalid G3,
  overlap blocker) is present.
- `tests/integration/test_sources.py` / venue test: `rh venue check` is optional;
  its absence no longer blocks verified export.
- Regression: traceability gates still block (reuse existing claim/G3/overlap
  blocker tests). Full `rh-dev` gate green.
