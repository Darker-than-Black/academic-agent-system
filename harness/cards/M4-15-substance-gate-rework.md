# M4-15 — Substance readiness gate + rework flow (ADR-023)

> Milestone M4. Modules `research-lab.md`, `claims-text.md`, `review.md`,
> `intake-rules.md`. Requirements FR-09, ADR-023. Tests new. Depends on M2-06
> (claims ledger), M3-02 (review), M4-14 (figures, for empirical). Base `main`.
> Addresses test-run feedback item 4 (core). Implements ADR-023.

## Goal

Stop the harness from producing an honest-but-empty article. Add an early
readiness gate and a post-draft substance report so the author is told, early and
explicitly, what to supply to make a real analysis — without the harness ever
inventing data (H6/H7).

## What this card delivers

- **`article_type`** — intake question + object field `{review | empirical |
  theoretical}`; `unknown` does not pass (H7). Drives which substance criteria and
  figure expectations apply.
- **Readiness gate (deterministic), bound before/at G1:**
  - review: fulltext-vs-metadata source ratio; count of material claims that can
    reach ≥ partial; synthesis present (not restatement); subquestion coverage.
  - empirical: presence of dataset/`runs`/`rows`, method, ≥ 1 planned result
    figure (M4-14).
  - Below the pack threshold → **blocker** findings listing exactly what is
    missing; does not proceed to full drafting until supplied or scope/type
    consciously changed. Nothing invented (H6).
- **Post-draft substance report (`rh ... substance`):** material claims that are
  unsupported / insufficient / unverifiable / demoted-to-background; for each, what
  is missing (fulltext of source X; microdata/codebook; own experiment; larger
  sample) and what to provide to raise support; plus a **"analysis-free" signal** —
  if the share of limitation / "could not" statements exceeds a threshold, a major
  warning "the article describes the absence of a result, not a result".
- **Rework loop** — the report feeds a repeatable cycle: author supplies
  data/sources/experiment → excerpts/claims/figures update → re-draft + re-report.
  Each step logged. Report envelope carries `next_actions` (who: author).
- **Thresholds in rulepacks** (`ua-fahove-b` / general), as data, draft.
- **Specific substance checks (test-run pasted items 1–4):**
  - *synthesis vs restatement* — flag results units that mostly restate single
    sources without cross-source synthesis (deterministic proxy: claims each
    citing one source, no comparative/aggregated claim; semantic depth → critic).
  - *effect-evidence detail* — a material "effect" claim with no structured
    evidence (direction/magnitude/sample/context from a fulltext excerpt) is
    flagged as needing extraction; never invented.
  - *scope/thesis calibration* — the stated topic/thesis vs the evidence base: if
    the corpus is mostly indirect (e.g. HE students, general special-ed tech) for
    a claim about a specific population (ООП), flag that the thesis overreaches and
    should be scoped to "gap + indirect evidence".
  - *conclusion-vs-evidence calibration* — a conclusion whose certainty wording
    ("підтверджено з помірною певністю", "погіршення успішності") exceeds the
    supported level of its claims is flagged to soften or cite.
  - *cross-unit consistency* — contradictory statements across units (e.g. intro
    "дані не містять змінної" vs result "не зміг перевірити") are flagged; a
    categorical claim must be downgraded to the verifiable form or documented.

## Not in this card

The figure model itself (M4-14) and the docx format (M4-12). No change to the
honesty rules — readiness/substance only measure and name deficits; they never
fabricate evidence or results (H6/H7). Semantic judgement of "synthesis vs
restatement" beyond deterministic proxies can be an integration-critic follow-up.

## Tests

`tests/integration/`: a review object with mostly-metadata sources + an unknown
material claim fails readiness with a listed deficit; supplying a fulltext excerpt
lets it pass. A drafted object with many limitation claims yields the analysis-free
warning and a substance report naming each gap + required input. Regression:
honesty gates unchanged. Full `rh-dev` gate green.
