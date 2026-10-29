---
description: Відновлення, статус і наступна дія без змін вмісту (rh continue).
argument-hint: "--object <ID> [--lang uk|en]"
---

Run `uv run rh --format json continue $ARGUMENTS` from the `harness/` directory.
Report the recovery findings (if any), the current stage and the single next
action, in the author's language. This command never changes content. Do not add
logic beyond running `rh` and presenting its result.
