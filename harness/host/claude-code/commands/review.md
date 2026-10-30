---
description: Review one unit (support verdicts) or the article integration.
argument-hint: [unit-id|article]
allowed-tools: Bash(cd *), Bash(uv run rh *)
---
Review `$ARGUMENTS`. For a unit: `rh review prepare --level unit --unit $ARGUMENTS`,
then the `unit-critic` subagent submits verdicts via `rh review submit` (the
harness rejects any verdict above the deterministic cap). For the article:
`rh review integration` (deterministic part) then the `integration-critic`
subagent. Report coverage as checked/denominator; never write "PASS".
