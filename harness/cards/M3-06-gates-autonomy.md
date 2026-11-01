# M3-06 — Gates G1–G3 and autonomy enforcement

> Milestone M3a. Module `lifecycle-records.md`. Requirements FR-33, FR-35.
> Test T35. Depends on M3-02. Base `main`.

## Goal

Stage gates G1–G3 and the chosen autonomy level (step / gates / batch) enforced
in `rh`, not by prompts — a stage that needs a gate cannot proceed without a
recorded approval, at every autonomy level (ASR-04).

## What this card delivers

- **`lifecycle/autonomy.py`** (core): `LEVELS = step|gates|batch` (default
  `gates`, ADR-015); `read(root)` / `set_level(root, level)` (persists to
  `object.json`); `gate_skip_finding(required_gate, approved_gates)` — a
  `lifecycle.autonomy_gate_skip` blocker when a required gate has no valid
  approval, the same at every level (FR-33). Never records a gate (H14).
- **`rh autonomy show | set <level>`** — `set` is human-only: in an agent
  channel it writes nothing and returns a request with `next_actions:
  who=author`, exit 3; `show` is read-only.
- i18n en+uk.

Gate definitions G0–GE and the generic `rh gate request|explain|record|list`
already exist (M1); G1–G3 record through that human-only path unchanged. GE
(ethics) enforcement is M3-07.

## Not in this card

Wiring `gate_skip_finding` into actual stage transitions (and `rh step`), and
the Submission/Publication records, locks and `revise`/`reviews` modes, are
M3-08. This card provides the autonomy state, the human-only mutation, and the
pure enforcement predicate so M3-08 can call it.

## Tests

`tests/unit/lifecycle/test_autonomy.py`: default/set/read, unknown level raises,
gate-skip present/absent, CLI show, CLI set human-only block (unchanged level).
Full `rh-dev` gate green.
