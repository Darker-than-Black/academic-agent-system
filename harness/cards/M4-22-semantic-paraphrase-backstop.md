# M4-22 — Semantic paraphrase backstop in the unit critic (ADR-026)

> Milestone M4. Module `review.md` (unit critic), `claims-text.md`.
> Requirements FR-14, ADR-026, rule `writing.source_paraphrase`. Depends on
> M4-20 (overlap vs sources) and M4-21 (overlap in review flow). Base
> `feat/m4-21-overlap-in-review` (stacked). Implements the semantic half of
> `writing.source_paraphrase`.

## Why

Deterministic overlap (`rh overlap`, M4-20/21) catches verbatim copying and
light word-swapping (shingle + lemmatization). It cannot catch a *close
paraphrase*: same sentence order and structure, synonyms swapped. That is the
real risk for an author who retells sources in their own words — the failure
mode the author named. Only a reader holding both texts can judge paraphrase
distance, so the backstop is semantic (an LLM critic), not another shingle pass.

## What this card delivers

- **`unit_critic.md`** gains a paraphrase-distance task. The unit-critic context
  pack already carries both the unit prose and each cited excerpt's own wording
  (`context.pack._add_evidence` → `evidence` items with the excerpt text), so no
  new context plumbing: the critic compares the two and flags
  `writing.source_paraphrase` (major) when the prose tracks a source's wording
  too closely without being a marked quotation.
- The finding says: make it a direct quotation (quotes + citation + page) or
  reword in the author's own words and structure keeping the citation (H6). A
  fragment legitimately retold in the author's own words, or the author's own
  conclusion, is not flagged. Genuinely original prose, never detector evasion
  (N4).
- **Major, not a blocker:** it guides the copyedit/rewrite pass (writer.md,
  ADR-026), it does not hard-block verified export.
- Subagents regenerated from the prompt.

## Not in this card

No deterministic code — the semantic check is the critic's judgement by design
(the deterministic half is the existing overlap shingle; duplicating it adds
nothing). No new role (ADR-002, one writer/critic per object). Codex-engine
parity of the same prompt follows the normal `rh-dev host generate` path.

## Tests

No new unit test — the change is a prompt the host generator renders into the
subagent. `rh-dev check` green (prompt/subagent parity guard, i18n, lint all
pass); `uv run rh-dev host generate claude-code` leaves the generated
`unit-critic.md` in sync with the prompt.
