# ML Branch

**Milestone(s).** M6 only. Heavy or paid compute and model training at scale — LATER (FR-39 heavy part).

**Requirements.** FR-04 (ML protocol), FR-05 and FR-06 (ML runs), NFR-08 (ML); ADR-009, ADR-013.

## Purpose

Extend the analysis sandbox to empirical ML studies: protocols with seeds, splits, primary metric and baseline; import of existing ML results; small CPU runs executed locally; tuple validation of ML numbers.

## Owned files

| Path (object folder) | Content |
|---|---|
| `protocol/ml-protocol.yaml` | Versioned protocol: question / hypothesis, datasets, splits, primary and secondary metrics, baseline, seeds, falsification criteria, resource limits |
| `runs/<R>/` | As `analysis-sandbox.md`, `origin: executed\|imported` |
| `results/rows.jsonl` | Rows with `split`, `condition`, `metric`, `seed`, `aggregation` |
| `harness/rulepacks/ml-empirical/` | ML reporting rules (e.g. seeds reported, baseline present) |

## Commands

| Command | Behaviour |
|---|---|
| `rh results import --ml DIR` | Imports runs and metrics with provenance; missing fingerprints listed |
| `rh run plan` / `rh run execute PLAN-ID` | Small CPU runs in the sandbox per protocol |
| `rh protocol revise` | New protocol version; a change of primary metric / splits after G1 → G2 required (T03) |

## Data contracts

02 §12 Run and Result row; additions: `split_id`, `seed`, `model_or_condition`, `metric_id`; protocol schema `ml-protocol.schema.json` (new, M6).

## Invariants

1. Changing the primary metric, split or inclusion after G1 creates a new protocol version and requires G2; old runs are kept.
2. Fewer seeds than the protocol says is a protocol deviation, never a silent budget saving (registry #27 note).
3. Imported ≠ executed ≠ simulated; failed ≠ succeeded (T04).

## Checks

| Check ID | Kind | Severity | Rule source |
|---|---|---|---|
| `ml.protocol_deviation` | D | blocker until G2 | FR-04 |
| `ml.tuple_mismatch` | D | blocker | ADR-009 |
| `ml.seed_count` | D | major | `ml-empirical` |
| `ml.baseline_missing` | D | major | `ml-empirical` |

## Reuse

| # | Origin | License | Mode | Note |
|---|---|---|---|---|
| 24 | AutoResearchClaw `paper_verifier.py` checks | MIT | idea only | Depends on rejected #25 |
| 37, 38 | AI-Scientist-v2 journal / tree search / review | AI Scientist Source Code License | idea only | Disclosure clause; no code |

## Tests

| Test | Fixture | Milestone |
|---|---|---|
| T04 (F1) | F1 | M6 |
| T05 (ML, N2) | F1, F3 | M6 |
| T03 (ML protocol part) | F1 | M6 |
| F2-H MV report | F2-H | M6 |

## Open points

- [?] Who prepares F2-H (`05-eval-base.md` does not say) — proposal: the author, same procedure as F4-H.
