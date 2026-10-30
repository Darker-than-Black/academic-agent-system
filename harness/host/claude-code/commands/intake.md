---
description: Провести анкетування об'єкта (rh intake) у розмові.
argument-hint: "--object <ID>"
---

Run `uv run rh --format json intake questions $ARGUMENTS` from the `harness/`
directory. Then, following `AGENTS.md`:

- Ask the returned questions one block at a time, in the conversation language.
- Use each question's `help` text when the author hesitates.
- Record each answer with `uv run rh intake answer --object <ID> --question <Qx>
  --value <…>` (or `--unknown`). Never guess an `unknown`.
- When intake completes, `rh` opens the G0 request — hand it to the author per
  `AGENTS.md` → Gates.

Do not add logic beyond running `rh` and presenting its result.
