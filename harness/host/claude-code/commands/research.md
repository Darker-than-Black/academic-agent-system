---
description: Run the research cycle for the current object (search → synthesis → counter-evidence).
argument-hint: [object-id]
allowed-tools: Bash(cd *), Bash(uv run rh *)
---
Run the research cycle for object `$ARGUMENTS` through the `rh` CLI, delegating to
the `researcher` subagent with a fresh-context pack. Follow each envelope's
next_actions: `rh search plan` → `rh search run`/`rh search log` → `rh screen` →
`rh excerpt` → `rh matrix`/`rh premise`/`rh positions`/`rh gaps` →
`rh counter-evidence` → `rh saturation`. Stop at any gate (who: author) and hand
it to the author. Never invent sources, results or approvals (H6).
