# M4-20 — Inline antiplagiarism + copyedit pass (ADR-026)

> Milestone M4. Modules `integrity.md` (overlap), `review.md`, `claims-text.md`.
> Requirements FR-30, FR-19, ADR-026. Depends on M3-10 (overlap), M4-16
> (cite-binding), M4-18 (writing pack). Base `main`. Implements ADR-026.

## Goal

Catch plagiarism early — during writing, not at the end — and make the writer
produce original scholarly prose that retells sources in the author's own words
and conclusions, while keeping attribution (H6). The aim is to genuinely not
plagiarise, never to evade a detector (N4).

## What this card delivers (first slice: rule-as-data + prompt)

- **Rule `writing.source_paraphrase`** in the `writing` pack (integrity, major,
  overridable): text too close to a cited source's wording is quoted (quotes +
  citation + page) or reworded in the writer's own words keeping its citation;
  borrowed wording is never passed off as original.
- **`writer.md` copyedit/rewrite pass** (ADR-026 — the same writer slot, not a
  new role; respects ADR-002 "one writer per object"): paraphrase into original
  prose at narrative depth, keep `[cite:X]` on borrowed specifics, treat the
  similarity gate as a helper, and refuse/ surface any detector-evasion
  instruction (N4). Regenerate the Claude Code subagents.

## Not in this card

Executable: extend `rh overlap` (`integrity/overlap.py`) to compare a drafted
unit against a **second corpus** — the cited sources (excerpts + `library.sqlite`
fulltext, runtime-only so no foreign fulltext enters git, H8) — in addition to
the author corpus; wire it as an inline gate in the writing flow; similarity
thresholds as rule-pack data (`ua-mon-phd` / `ua-fahove-b`), draft. Optional
export of clean material for the institution's external service (Unicheck /
StrikePlagiarism) — the external paid run stays with the author (H9/H11). No
paid detector is integrated; nothing is rewritten to evade detection (N4).

## Tests

`tests/unit/rules`: the `writing` pack still lints clean with the new rule.
`rh-dev check` green. (Overlap-vs-sources behaviour tests land with the
executable slice.)
