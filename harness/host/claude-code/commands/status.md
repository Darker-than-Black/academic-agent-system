---
description: Показати статус об'єкта (rh status): етап, гейти, блокери, наступна дія.
argument-hint: "--object <ID> [--lang uk|en]"
---

Run `uv run rh --format text status $ARGUMENTS` from the `harness/` directory and
show the rendered report to the author in their language. If `next_actions`
contains an author action (a gate), hand it over per `AGENTS.md` → Gates. Do not
add logic beyond running `rh` and presenting its result.
