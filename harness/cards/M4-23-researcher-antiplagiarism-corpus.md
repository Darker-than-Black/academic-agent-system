# M4-23 — Researcher builds the antiplagiarism corpus from screened sources (ADR-026)

> Milestone M4. Module `research.md` (researcher), `sources.md`, `integrity.md`.
> Requirements ADR-026, FR-30. Depends on M4-20/M4-21 (overlap vs sources in the
> review flow) and the existing `rh source fetch-oa` + `rh library index` chain.
> Base `feat/m4-22-semantic-paraphrase` (stacked). No new code.

## Why

Overlap and the semantic backstop can only compare against source full text that
is present in `sources/pagetext/`. Today that is populated ad hoc, so the
antiplagiarism check effectively sees only whatever was ingested by hand —
usually just cited sources. The author asked to scan external sources, not only
their own drafts. The whole fetch→ingest chain already exists
(`rh source fetch-oa` resolves legal OA full text via Unpaywall → `sources/
fulltext/`; `rh library index` extracts every stored full text → `sources/
pagetext/<S>.jsonl`). The gap is orchestration: nobody tells the researcher to
run it. This card closes that gap in the researcher flow.

## What this card delivers

- **`researcher.md`** gains a step (after excerpting): for screened-in sources
  with a legal OA location, `rh source fetch-oa <ids>` then `rh library index`,
  so every stored full text enters the antiplagiarism corpus. The drafted text
  is then checked against the external sources actually read — not only the ones
  finally cited — by `rh overlap --against sources` and `rh review fulltext`.
- Boundaries kept explicit in the prompt: full text is gitignored, runtime-only
  (H8); Unpaywall is free so H9 is not engaged, a paid fetch stays gated; no OA
  location means the source simply has no full text here and stays so, never a
  fabricated one (H6/H7).
- Subagents regenerated from the prompt.

## Not in this card

No change to `fetch_oa`/`ingest` themselves — they already work. No paid
full-text provider and no web-scale index: comparison against the whole web or
subscription databases stays with an external paid detector
(Unicheck / StrikePlagiarism), outside the harness (H9/H11). Auto-fetch from the
search step without a screening decision is deliberately out: only screened-in
sources are fetched, to keep the corpus relevant and the fetch volume bounded.

## Tests

No new unit test — the change is a prompt the host generator renders into the
subagent; the `fetch-oa`/`index` commands have their own M2/M3 coverage.
`rh-dev check` green; `uv run rh-dev host generate claude-code` leaves the
generated `researcher.md` in sync with the prompt.
