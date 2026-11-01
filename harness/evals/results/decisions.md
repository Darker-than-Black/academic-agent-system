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

# M2 gate — decisions

| Date | Decision |
|---|---|
| 2026-11-01 | approve — M2 deterministic suite `rh eval run --suite M2`: 20/20 pass. M2-semantic scored against the first blind host (С) run `F4W-host-2026-11-01.run.json` (model claude-fable-5-1): 4/4 cases pass. Hard gates met: MF critical false PASS = 0, MA invented = 0. |

## M2 semantic baseline → evidence

First real host run for the semantic suite, produced blind per M2-19 (two flagship
`claude-fable-5-1` subagent passes saw only `manuscript.md` + `sources.yaml` + the
3 available OA full texts (EN1, UA3, UA4) + the EN6 injection doc + the D1–D14
codebook — never `annotation.yaml`, H6). `rh eval align-run` mapped the 114
extracted claims to gold claim_ids by span overlap (44/44 gold matched, 70
spurious); raw sha256 sealed in `producer.note`.

Hard gates (must hold for M2):
- MF critical false PASS = 0 — no critical claim marked `supported` where the gold differs. MET.
- MA invented = 0 — no fabricated author-contribution position. MET.

Report-only baselines on M2 (thresholds switch on in M3/M5), each with n and 95% Wilson CI:
- MX recall 1.000 (n=40); precision 0.448 (n=87) — all material claims extracted, over-extraction expected.
- MV accuracy 0.455 (n=44); macro-F1 0.536; critical recall 0.667 (n=9).
- MS recall 0.824 (n=17); precision 0.824; missed D3, D9, per-claim D13 on C-001.

Coverage note: only 3 of 12 sources had an OA full text at run time; the rest were
metadata-only, so many content claims are `insufficient`. A higher MV/MS baseline
needs more full texts and a re-run (new dated artifact).

Non-deterministic / manual (in PRs, not here): the host run artifacts live in
`evals/fixtures/F4W/runs/F4W-host-2026-11-01.{raw,run}.json`. Holdout F4-H is run
separately by the author (H1); its aggregate row is in `holdout-log.jsonl`.