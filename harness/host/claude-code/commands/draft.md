---
description: Draft one unit from its brief with visible placeholders.
argument-hint: [unit-id]
allowed-tools: Bash(cd *), Bash(uv run rh *)
---
Draft unit `$ARGUMENTS` via the `writer` subagent. Read the brief
(`rh brief check`), then write only through a previewed `rh unit diff` followed by
`rh unit write --request "<author's words>"`. Leave `[[AUTHOR: ...]]` where the
author must decide. Never overwrite an author edit (a conflict stops you). Every
material claim needs evidence; invent nothing (H6).
