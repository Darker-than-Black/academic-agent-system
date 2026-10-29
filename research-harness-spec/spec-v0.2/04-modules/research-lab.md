# Research lab: protocol, search, synthesis, journal

**Milestone(s).** M2 (cards M2-03, M2-04, M2-05). Analysis sandbox — M3 (`analysis-sandbox.md`). ML protocol — M6 (`ml.md`).

**Requirements.** FR-03, FR-04, FR-29, FR-54 parts 3 and 5, FR-56; ADR-013, ADR-020; `06-research-agent.md` §3.3, §3.5, §4.

**Purpose.** Give the researcher role a bounded, recorded research cycle: question → protocol → search plan with stopping rule and budget → search → extraction → synthesis with positions and gaps → counter-evidence for every central claim → findings with evidence refs. Everything the researcher does leaves a trace the author and the critic can check.

**Owned files.**

| Path (object) | Content |
|---|---|
| `protocol/protocol-v<N>.yaml` | Protocol by `study_kind` (below); immutable after G1; new version for every change |
| `lab/search-plan-v<N>.yaml` | Resources, queries per resource, inclusion / exclusion criteria, saturation rule, budget |
| `lab/search-log.jsonl` | One line per query (incl. manual exports) |
| `lab/screening.jsonl` | Include / exclude decision per candidate with reason |
| `evidence/excerpts.jsonl` | Excerpts (02 §12) |
| `evidence/matrix.jsonl` | Synthesis matrix rows |
| `evidence/premises.jsonl` | Premises and definitions (conceptual) |
| `lab/positions.yaml` | Position map: positions, sources per position, who disputes whom |
| `lab/gaps.yaml` | Gaps: question without answer in the matrix + evidence refs |
| `lab/counter-evidence.jsonl` | Per central claim: queries run, results, outcome `found` / `not_found_after_search` |
| `lab/saturation.jsonl` | Per screening batch: new themes / positions added |
| `lablog/journal.jsonl` | Lab journal (FR-54 p.5): questions, hypotheses, plan changes, dead ends, protocol deviations, cost, model IDs |
| `lab/findings.yaml` | Research findings handed to the writer, each with evidence refs and confidence |

Harness: `research_harness/lab/{protocol.py, plan.py, searchlog.py, screening.py, matrix.py, positions.py, gaps.py, counter.py, saturation.py, journal.py, findings.py}`.

**Commands.** `rh protocol draft|show|freeze` (freeze opens a G1 request), `rh search plan` (validate and store a plan the researcher wrote), `rh search run --adapter A --query Q` (API adapters; writes log), `rh search log --resource R --query Q --results N [--file F]` (manual searches and exports), `rh screen --source S --include|--exclude --reason R`, `rh excerpt add --source S --page P --text …`, `rh matrix add|show`, `rh premise add`, `rh positions set`, `rh gaps set`, `rh counter-evidence record --claim C …`, `rh saturation check`, `rh lab journal add --kind K --text …`, `rh findings set`.

All `add` / `set` commands take a JSON or YAML file (`--file`) as the normal input; agents write a handoff file and pass it. Single-field flags are conveniences for humans.

**Data contracts.**

Protocol (`literature-narrative`, `conceptual`; the pack defines required fields):

| Field | Literature (narrative) | Conceptual |
|---|---|---|
| `question`, `scope`, `language_scope`, `period` | required | required |
| `resources[]`, `search_strategy` | required (descriptive) | optional |
| `inclusion`, `exclusion` | required | optional |
| `synthesis_method` | required (thematic / comparative) | — |
| `concepts[]`, `argument_structure`, `assumptions[]` | — | required |
| `saturation_rule` | `{batch_size, no_new_items_in_batches}` required | — |
| `counter_evidence_rule` | required: which claims count as central | required |
| `limits` | required: what the review does not claim (e.g. not systematic) | required |
| `version`, `previous`, `change_reason` | required from v2 | same |

Search log line: `{id, at, resource, mode: api|manual_export|manual_record|browser_assisted, query (exact, per resource syntax), filters, status (resource_status), results_total?, records_returned, export_file_sha256?, plan_version, budget_used}`.

Matrix row, premise, excerpt — 02 §12. Counter-evidence record: `{claim_id, queries: [search_log_id], outcome, sources_found: [S-id], note}`.

Findings handed to the writer: `{id, statement, kind: synthesis|gap|position|definition|counter_position, evidence: [{type, id}], strength: strong|moderate|weak|contested, limits, open_questions}`.

**Invariants.**
1. No search without a stored plan; no plan without a stopping rule and budget (FR-56).
2. "Not checked" ≠ "nothing found": a resource that was unavailable or skipped appears as a coverage gap, never as zero results (FR-03, FR-20).
3. Every excerpt has a locator and access level; every matrix row and finding points to excerpts (FR-29).
4. Every central claim of the protocol has a counter-evidence record before findings are handed over; "nothing found" lists the queries (FR-56, T60).
5. The cycle stops on saturation, budget or the author's decision; the stop reason and what remains uncovered are recorded (T61).
6. Protocol versions are immutable; changing `question`, `inclusion`, `exclusion` or `synthesis_method` after G1 creates a new version and requires G2 (T03).
7. Citation counts are never the only quality criterion (`07-components.md` literature procedure).
8. The review is never described as systematic unless the scoping/systematic profile is used (LATER, FR-15c).

**Checks.**

| ID | Kind | Severity | Source |
|---|---|---|---|
| `protocol.required_missing` | D | blocker for G1 | pack `literature-narrative` / `conceptual` |
| `protocol.changed_after_g1` | D | blocker until G2 | T03 |
| `search.no_plan`, `search.plan_no_stop_rule` | D | blocker | FR-56 |
| `search.log_incomplete` (missing query, status or date) | D | major | FR-03 |
| `search.coverage_gap` | D | info, shown in status | FR-20 |
| `screening.decision_without_reason` | D | major | 02-lifecycle A2 |
| `excerpt.no_locator` | D | blocker | FR-29 |
| `matrix.row_without_excerpt` | D | major | FR-29 |
| `premise.no_source_no_assumption` | D | major (D11) | T30 |
| `counter.missing_for_central_claim` | D | blocker for handing findings | FR-56 |
| `saturation.stop_unrecorded` | D | major | T61 |
| `synthesis.quality` (relevance, gaps, positions) | S | advisory | critic role |

**Reuse.** OPM #4 literature-engine, #9 method / theory / positioning engines (shortened), #7 idea-engine (A1), K-Dense `literature-review`, `scientific-critical-thinking`, `hypothesis-generation` — as role procedures, rewritten to these commands and statuses. Details: `06-reuse-adoption.md`.

**Tests.** T01 (discovery plan, M2 part), T03, T20, T30, T59 (log part), T60 (baseline), T61; fixtures F4-W, mocks of unavailable resources.

**Open points.** [P] Default saturation rule: batches of 10 screened sources, stop after 2 consecutive batches without new themes or positions — the author can change it per protocol. [P] Bibliometrics (keyword co-occurrence, clusters) are listed in FR-54 p.3 but need the sandbox; scheduled with the sandbox in M3.
