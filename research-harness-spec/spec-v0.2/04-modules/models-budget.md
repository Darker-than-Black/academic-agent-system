# Model tiers, call log, budget

**Milestone(s).** M1 (card M1-12: tier config, resolve / downgrade / log); M2 (every agent call is logged; T63 gate); M3 (budget controller, FR-13 / T12).

**Requirements.** FR-13, FR-55, NFR-05; ADR-017, ADR-020.

**Purpose.** Each role runs on the model tier it needs, nobody silently downgrades, every call is recorded, and spending is checked before it happens. Paid calls are off by default.

**Owned files.** Object: `.rh/model-calls.jsonl`, `budget.yaml` (M3). Harness: `harness/config/{roles,model-tiers}.yaml`, `research_harness/{models,budget}/`.

**Commands.** `rh model resolve|downgrade|log` (M1); `rh budget show|set|check` (M3).

**Data contracts.** 02 §10. Budget (M3), added here:

| Field | Rule |
|---|---|
| `budget.yaml` | `{scope: object|task, limits: {model_calls?, tokens?, cost?, wall_time_s?, external_requests?}, paid_calls: disabled|enabled, enabled_by?: approval_id, thresholds: [0.5, 0.8, 1.0]}` |
| Budget state | Computed from `model-calls.jsonl` and adapter request logs; any `unknown` usage makes the state `unknown`, never `ok` |

**Invariants.**
1. Tier → model mapping lives only in config; prompts and role definitions name tiers, not models (ADR-020).
2. A missing model for the required tier stops the call (exit 3) unless an explicit downgrade with a reason was recorded (FR-55).
3. Missing telemetry is `"unknown"`, never 0 (NFR-05).
4. Paid calls are disabled by default; enabling them needs an intake answer (Q9) and a limit (ADR-017 p.1).
5. At 100% of any limit the task stops with partial artifacts and a status line; 50% and 80% produce info findings (registry #22 thresholds).

**Checks.**

| ID | Kind | Severity | Source |
|---|---|---|---|
| `model.tier_unmapped` | D | blocked | FR-55 |
| `model.downgrade_unrecorded` | D | blocker | FR-55 |
| `model.call_unlogged` (agent handoff without call ID) | D | major | FR-55 |
| `budget.threshold_50`, `budget.threshold_80` | D | info | #22 |
| `budget.exhausted` | D | blocked | FR-13 |
| `budget.unknown_usage` | D | major | NFR-05 |
| `budget.paid_call_disabled` | D | blocked | ADR-017 |

**Reuse.** AutoResearchClaw #22 `cost_guard.py` (M3) with an added `unknown` state. Details: `06-reuse-adoption.md`.

**Tests.** T63 (M1 config, M2 gate), T12 (M3); fixtures F5b + host mock.

**Open points.** [?] Whether Claude Code exposes per-call token usage to the agent; if not, calls log `"unknown"` and budget relies on call counts and wall time (to verify in M2-13).
