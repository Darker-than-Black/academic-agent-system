---
description: Export a draft of the current object to .docx or .md.
argument-hint: [docx|md]
allowed-tools: Bash(cd *), Bash(uv run rh *)
---
Export a draft with `rh export --mode draft --format $ARGUMENTS`. Show the author
the gaps report (placeholders, unsupported claims, stale summaries, unresolved
citations) and the export directory. Foreign full texts and private materials are
never included (H8).
