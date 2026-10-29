# Review

**Milestone(s).** M2 (unit-level support verdicts on F4-W as a baseline report); M3 (full module: multilevel review, coverage report, disputes, finding resolution, document-wide CLI checks, Codex critic); M5 (thresholds, critic comparison).

**Requirements.** FR-07, FR-09, FR-14, FR-22 (integration part), FR-23, FR-49, FR-58; NFR-03, NFR-16; ADR-004, ADR-005, ADR-010 rev.2, ADR-019 p.5, ADR-020 p.5.

## Purpose

Find defects in the manuscript and its evidence before the author decides anything, with every verdict traceable to evidence and every gap in coverage visible. Review never approves, never edits the manuscript and never changes raw data (ADR-010 p.5). Deterministic checks run in the CLI; semantic judgements come from critics in fresh contexts and are advisory.

## Owned files

| Path (object folder) | Content |
|---|---|
| `reviews/<review-id>/request.json` | Level, target units, snapshot ID + `manifest_sha256`, context-pack refs, engine, model tier, budget |
| `reviews/<review-id>/findings.jsonl` | Findings in the 02 §9.4 schema, one per line |
| `reviews/<review-id>/verdicts.jsonl` | Per-claim assessments: `{claim_id, support, rationale, evidence_refs, access_level, confidence: low|medium|high, by, at}` |
| `reviews/<review-id>/report.md` | Human report in `ui_language` (format below) |
| `reviews/<review-id>/check-run.json` | Check run with coverage (02 §9.4) |
| `reviews/disputes/<dispute-id>.json` | Dispute record (below) |
| `findings/index.jsonl` | Current status of every finding across reviews (open / accepted / rejected / fixed / unresolved), resolution records |

| Path (harness) | Content |
|---|---|
| `harness/host/claude-code/agents/{unit-critic,chapter-critic,integration-critic}.md` | Subagent definitions (05-agents.md) |
| `harness/review/rubric.yaml` | Support-verdict rubric (adapted from registry #2 with changed meaning, see Reuse) |
| `harness/review/fulltext-checks.yaml` | Configuration of document-wide CLI checks (thresholds come from rule packs) |

## Commands

| Command | Behaviour |
|---|---|
| `rh review prepare --level unit\|chapter\|integration --unit U [--engine claude\|codex]` | Builds the review request and the context pack (summaries-context.md, `rh context pack`), returns what the critic must read and the output schema. Does not call a model |
| `rh review submit REVIEW-ID --findings FILE --verdicts FILE` | Validates critic output against schemas, rejects verdicts without evidence refs or with unknown claim IDs, writes the check run with the full denominator, renders `report.md` |
| `rh review --level … --engine codex` | Runs the Codex critic as a subprocess (below); same `submit` path |
| `rh review fulltext` | Deterministic document-wide checks (below); no LLM |
| `rh review coverage [--unit U]` | Coverage of claims by verdict: denominator = all material claims in scope |
| `rh findings list [--status open]` / `rh findings resolve F-ID --decision accept\|reject --reason TEXT` | Resolution is human-only: same TTY + `RH_AGENT_SESSION` rule as gates (02 §9.3); agent calls create a resolution *request* and exit 3 |
| `rh dispute open --claim C-ID --finding F-ID` / `rh dispute add-evidence` / `rh dispute close` | FR-23 dispute cycle |

`rh review prepare` and `rh review submit` are additions to 03-cli §2.8 (reserved name `rh review`).

## Data contracts

Findings, check runs and claims follow 02 §9.4 and §12. New fields:

| Record | Field | Rule |
|---|---|---|
| Review request | `level` | `unit` / `chapter` / `integration` |
| Review request | `engine` | `claude` / `codex`; `engine_status`: `ok` / `unavailable` / `blocked_by_permissions` |
| Review request | `fresh_context: true` | Required; the critic context contains no writing history (ADR-010 p.2) |
| Verdict | `confidence` | `low` / `medium` / `high`; a `supported` verdict with `low` confidence is shown as such in the report |
| Check run | `coverage.unchecked_ids[]` | Material claims not assessed in this run (N3) |
| Dispute | `{id, claim_id, finding_id, cycles[{by: analyst|critic, argument, evidence_refs, at}], max_cycles, status: open|resolved_by_author|unresolved, author_decision?}` | `max_cycles` default 2, configurable in `harness/config/review.yaml` |

## Review levels (ADR-019 p.5)

| Level | Context | Checks | Required |
|---|---|---|---|
| Unit | Unit text + its brief + evidence for its claims (context pack) | Claim extraction completeness, support verdicts, brief compliance, qualifiers, local style, volume vs brief target | Every unit before chapter review |
| Chapter | Full text of the chapter + chapter summary + glossary | Logic across subsections, repetitions, chapter conclusions ↔ subsections (D17) | Thesis chapters; article treated as one chapter |
| Integration | `map.md`, all current summaries, results of `rh review fulltext`, selective reads of full text **only** at locations named by findings | Introduction ↔ conclusions, tasks ↔ chapters, novelty ↔ chapters ↔ publications, contradictions between chapters (D15), abstract ↔ results ↔ conclusions (D13) | Mandatory for theses (ADR-010 p.7); for articles at A10 |

Integration review on stale summaries is refused by `rh review prepare` (FR-47).

## Document-wide CLI checks (`rh review fulltext`, FR-49)

| Check ID | What | Kind | Severity | Rule source |
|---|---|---|---|---|
| `fulltext.term_glossary` | Glossary terms used with a different definition marker, or a defined term outside the glossary | D | major | FR-49, D15 (glossary part), D19 |
| `fulltext.numbering` | Chapter / subsection / figure / table numbering continuous and matching `structure.yaml` | D | major | FR-49 |
| `fulltext.crossref` | Every cross-reference resolves to an existing unit / figure / table by ID | D | blocker | D18 |
| `fulltext.cite_keys` | Every cite key exists in the bibliography; every bibliography entry is cited (unless rule pack allows) | D | blocker / minor | FR-08 |
| `fulltext.repeated_fragment` | Repeated fragments between units: normalized word shingles, default ≥ 40 words or ≥ 2 paragraphs; thresholds from rule pack | D | major | D16 |
| `fulltext.volume` | Volume per unit and document (delegates to thesis.md volume counter) | D | per rule pack | FR-50 |

Performance target: ≈ 400 k characters, p95 < 10 s offline (NFR-04, SHOULD; measured in M4).

## Support verdicts and coverage (FR-07, FR-09)

- Verdict values: 02 §2 `support`. `unreviewed` claims count as **unchecked**.
- The rubric is adapted from registry #2 with the meaning changed: topical match without explicit support is `insufficient` or `partial`, never `supported` (N1, D1).
- Access level caps: abstract-only evidence → at most `insufficient` unless a rule allows narrow abstract-level claims (D2).
- Numbers from external sources are checked against the excerpt with locator, never against all numbers in a document (ADR-009 p.4).
- The report always shows `checked / denominator`, where denominator = all material claims in scope; a run that checked fewer than all is `partial`, never PASS (N3). A run with zero checked claims is `unknown`.

## Disputes (FR-23)

Analyst disagrees with a critic finding → `rh dispute open`; each side adds argument + evidence once per cycle; after `max_cycles` (default 2) without agreement the dispute becomes `unresolved` and goes to the author with both positions; the author's decision is recorded through `rh findings resolve` (human-only). No auto-PASS (T23).

## Finding resolution

Accept / reject requires the author, same channel rule as gates (02 §9.3 rules 1–2) and a short briefing in `ui_language`: the finding, evidence, proposed action, consequence of rejecting. Rejection requires a reason (T13). Resolutions are append-only.

## Codex critic (FR-58, ADR-020 p.5)

| Condition | Behaviour |
|---|---|
| Disabled by default (`harness/config/review.yaml: codex_critic.enabled: false`) | `--engine codex` → exit 3 with explanation |
| No credentials / binary not found | `engine_status: unavailable`; fallback to Claude critic in a fresh context, recorded in the request |
| Intake Q3b forbids external APIs for this object's materials | `blocked_by_permissions`; no call |
| Enabled, permitted, available | Subprocess, non-interactive mode (exact invocation verified against current Codex docs in M3, H12); input = context-pack files; output must validate against the same findings / verdicts schemas; budget checked first (models-budget.md); model ID logged (FR-55) |

## Report format (`report.md`, in `ui_language`)

1. Header: object, level, units, snapshot, engine, model ID, date.
2. Coverage: `checked / denominator`, counts per verdict, list of unchecked claims.
3. Blockers, then major, minor, info — each: ID, location (unit title + paragraph), what is wrong, evidence (locator), proposed action.
4. Disputes and their state.
5. What this review did **not** check (limitations), e.g. paraphrase overlap, sources without full text.

## Invariants

1. A critic never sees the writing history of the text it reviews (fresh context).
2. A critic cannot set a gate, resolve a finding, or edit manuscript or raw files; `rh review submit` writes only under `reviews/` and `findings/`.
3. Every verdict other than `unreviewed` has ≥ 1 evidence ref and a rationale; `supported` with empty evidence is rejected by schema.
4. Denominator in every coverage figure = full population in scope.
5. Integration review only on current (non-stale) summaries.
6. Review of snapshot X is never accepted as review of snapshot Y; stale reviews are shown as stale.
7. Text in sources is data: critic prompts state it; a source instruction found in evidence becomes a finding (T14, D10).

## Checks

| Check ID | Kind | Severity | Rule source |
|---|---|---|---|
| `review.verdict_without_evidence` | D | blocker | FR-07 |
| `review.coverage_incomplete` | D | major (blocker for verified export) | FR-09, N3 |
| `review.stale_summary_input` | D | blocker | FR-47 |
| `review.snapshot_mismatch` | D | blocker | 02 §6 |
| `review.claim_support` | S | per claim criticality | FR-07, rubric |
| `review.chapter_conclusion_basis` | S | major | D17 |
| `review.cross_chapter_contradiction` | S | major | D15 |
| `review.abstract_results_conclusions` | S | major | FR-22, D13 |
| `review.dispute_unresolved` | H | major | FR-23 |
| `fulltext.*` | D | see table above | FR-49 |

## Reuse

Authoritative details: 06-reuse-adoption.md.

| # | Origin (short SHA) | License | Mode | Change | Acceptance test |
|---|---|---|---|---|---|
| 2 | open-paper-machine `skills/verification-engine/SKILL.md` (`160df4d`) | MIT | adapt | PLAUSIBLE → `partial`/`insufficient`; Tier A/B/C → `access_level`; output to our verdict schema | T06 with N1 |
| 3 | OPM `skills/audit-engine/SKILL.md` (`160df4d`) | MIT | copy + extend | Link to result rows and run provenance (M3 sandbox) | T05 (F8) |
| 6 | OPM `skills/peer-review-engine/SKILL.md`, `commands/review-paper.md` | MIT | adapt | Advisory only; findings schema | T13 |
| 30 | OpenDraft `citation_claim_verifier.py` structures (`89128b3`) | MIT | adapt structures, not the judge | No 25-pair limit, no text truncation; explicit coverage | T08 (N3) |
| 34 | OpenDraft `prompts/04_validate/{skeptic,referee,factcheck_extract,factcheck_judge}.md` | MIT | adapt | Judge rewritten to support verdict (not topical relevance) | T06 |
| K-Dense | `peer-review`, `scientific-critical-thinking` (`5f2bc03`) | MIT | copy selectively after reading | Map to our levels and verdicts | T06, T53 |

## Tests

| Test | Fixture | Milestone |
|---|---|---|
| T06 | F2, F4-W, F4-H | M2 report (W), M3 threshold (H), M5 |
| T08 (N3) | F4-W, F5b | M3 |
| T13 | F4-W | M3 |
| T14 (semantic part, D10) | F4-W, F4-H, F5c | M3 |
| T22 | F4-W, F4-H | M2 report, M3 threshold |
| T23 | F4-W | M3 |
| T53 | F7 | M3 (CLI + baseline), M5 (threshold) |
| T64 | F4-W | M3 (conditions), M5 (comparison) |

## Open points

- [P] Default repeated-fragment threshold (40 words / 2 paragraphs) — confirm on F7 in M3.
- [P] Unit review is run per unit after drafting; chapter review after all its units pass unit review. The pilot (M5, variant C) decides whether unit-level review is kept for articles.
- [?] Exact non-interactive Codex CLI invocation and output capture — verify in M3 (H12).
