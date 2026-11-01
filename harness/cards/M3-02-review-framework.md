# M3-02 — Review framework (verdict schema, evidence, coverage)

> Milestone M3a. Module `review.md`. Requirements FR-07, FR-09, FR-14.
> Test T08 (N3). Depends on M2 (review v0, M2-11).

## Goal

Formalise the verdict contract and coverage so critics (M3-03) have a schema to
emit against and every gap in coverage is visible. Builds on review v0.

## What this card delivers

- **`schemas/verdict.schema.json`** — the reviewer verdict record
  (`claim_id, support, rationale, evidence_refs, access_level, confidence,
  by, at`). Invariant 3: any non-`unreviewed` verdict requires `evidence_refs`
  (≥1) **and** a rationale — a `supported` verdict with empty evidence is
  invalid by schema. `unreviewed` needs neither.
- **Evidence enforcement in `rh review submit`** — a non-`unreviewed` verdict
  with no evidence ref is rejected as `review.verdict_without_evidence`
  (blocker); malformed verdicts as `review.verdict_invalid`. The existing
  `review.unknown_claim` and `review.verdict_cap_exceeded` checks are unchanged.
  Nothing is stored on any rejection.
- **Richer assessment** — `evidence_refs`, `access_level`, `confidence` are
  carried into the stored claim assessment (claim schema + handoff schema
  extended with these optional fields).
- **`rh review coverage --unit U`** — coverage of material claims by verdict;
  denominator = all material claims in scope (invariant 4). Status `ok` when
  complete, `partial` when some unchecked, `unknown` when none checked (N3);
  `review.coverage_incomplete` (major) is surfaced when incomplete. `submit`
  attaches the same coverage + finding to a unit-level result.

## Deferred to later M3a cards

- `reviews/<id>/check-run.json` as the formal 02 §9.4 artifact (needs a bound
  `snapshot_id` and an `unchecked_ids` field on the check-run schema) and
  `report.md` rendering → with the critics/export cards.
- `review-request` schema with `snapshot_id`/`manifest_sha256`/`engine`/
  `fresh_context` and the `unit|chapter|integration` level rework → M3-03/04,
  where the critic call and snapshot binding land.
- `rh review fulltext`, disputes, `rh findings resolve`, Codex critic →
  M3-04/05/17.

## Tests

`tests/integration/test_review_v0.py`: v0 cap/coverage tests updated to carry
`evidence_refs`; new `test_verdict_without_evidence_is_rejected`,
`test_coverage_incomplete_finding`, and assertions that the M3-02 fields persist
and `by_verdict`/`status` are reported. Schema examples under
`tests/unit/schemas/examples/verdict/`. Full `rh-dev` gate green.
