# M1 gate — decisions

| Date | Decision |
|---|---|
| 2026-10-30 | M1 evaluation suite run via `rh eval run --suite M1`: 17/17 deterministic exit tests pass (see `M1-2026-10-30.json`). M1 ready for the author to review and merge. |

## M1 exit tests → evidence

Each case in `evals/cases/M1/*.yaml` maps an M1 exit-test ID to the pytest node(s)
that verify it; the runner executes them and records exit codes in the dated
results file. Deterministic tests must be 100% — they are.

Non-deterministic / manual checks (recorded in the relevant PRs, not here):
the M1-10 interactive `rh gate record` transcript (uk) and the M1-14 Claude Code
session excerpt (uk).
