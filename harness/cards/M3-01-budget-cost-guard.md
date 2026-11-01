# M3-01 — Budget and cost guard

> Milestone M3a (split approved 2026-11-02). Module `models-budget.md`.
> Requirements FR-13, NFR-05. Test T12. Depends on M2.

## Goal

Limits checked before every LLM / compute / paid call; `unknown` usage never
counts as `0`; at 100% of any limit the task stops with partial artifacts.

## What this card delivers

- **`schemas/budget.schema.json`** — the object's `budget.yaml`:
  `{scope, limits{model_calls,tokens,cost,wall_time_s,external_requests},
  paid_calls, enabled_by?, thresholds}`. `paid_calls: enabled` requires
  `enabled_by` (schema `if/then`).
- **`research_harness/budget/`** (core, LLM-free — H5):
  - `usage_from_calls(root)` aggregates `.rh/model-calls.jsonl` (and an optional
    `.rh/external-requests.jsonl`). Any contributing `"unknown"` poisons that
    total to `"unknown"` — never `0` (NFR-05, invariant 3).
  - `evaluate(budget, usage)` → per-limit ratios, threshold findings
    (`budget.threshold_50/80` info, `budget.exhausted` blocker), overall state
    (`exhausted` > `unknown` > `ok`).
  - `check(budget, usage, paid=…)` → the pre-call guard; `allowed` is false on
    any blocker. Paid calls blocked unless `paid_calls: enabled` **and** an
    `enabled_by` approval id is present (ADR-017/ADR-021, invariant 4).
- **`rh budget show|set|check`** (`cli/budget.py`):
  - `show` — limits, usage, state (+ findings).
  - `set --limit KEY=VALUE … --scope … --paid enabled --approval AR-id` —
    enabling paid without an approval is `blocked`, writes nothing.
  - `check [--paid]` — exit 0 allowed, exit 3 blocked.
- i18n keys (en + uk); checks map to the severity enum
  (`blocked`→`blocker`, info, major).

## Checks (models-budget.md)

| check_id | severity |
|---|---|
| `budget.threshold_50`, `budget.threshold_80` | info |
| `budget.exhausted` | blocker |
| `budget.unknown_usage` | major |
| `budget.paid_call_disabled` | blocker |

## Reuse note (H4)

AutoResearchClaw #22 `cost_guard.py` is cited by the spec as a reference. This
implementation is clean-room from the module contract with an added `unknown`
state; no third-party text was copied, so no adoption record is triggered. A
literal adoption would need `harness/third_party/manifest.json` +
`THIRD_PARTY_NOTICES.md` as a separate step.

## Not in this card

Wiring the guard into the subagent-call path and `rh status`, and the
`external-requests.jsonl` producer (adapter request logs), land with the review
and host-adapter cards that make those calls. `budget.unknown_usage` already
covers the "no telemetry yet" case.

## Tests

`tests/unit/budget/test_controller.py` (usage/unknown propagation, thresholds,
exhaustion, paid gate), `tests/unit/budget/test_cli.py` (set/show/check,
approval gate), schema examples under `tests/unit/schemas/examples/budget/`.
Full `rh-dev` gate green.
