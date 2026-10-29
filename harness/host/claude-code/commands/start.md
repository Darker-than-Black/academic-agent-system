---
description: Почати нову статтю або дисертацію (rh start) і показати питання анкети.
argument-hint: "<назва> [--kind article|thesis]"
---

Run `uv run rh --format json start $ARGUMENTS` from the `harness/` directory.
Then, following `AGENTS.md`:

- Present the created object id and folder to the author in their language.
- Ask the returned intake questions one block at a time, in the conversation
  language, using each question's `help` text if the author hesitates.
- Record answers with `rh intake answer`; never guess an `unknown`.

Do not add logic beyond running `rh` and presenting its result.
