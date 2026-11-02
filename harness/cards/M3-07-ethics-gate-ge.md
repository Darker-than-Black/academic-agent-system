# M3-07 — Ethics gate GE

> Milestone M3a. Module `lifecycle-records.md`. Requirement FR-31. Test T33.
> Depends on M3-06. **Stacked on `m3/M3-06-gates-autonomy`.**

## Goal

Block A6 (evidence collection) without an external ethics approval when the
study involves human participants — enforced in `rh`.

## What this card delivers

- **`lifecycle/ethics.py`** (core):
  - `requires_ethics(answers)` — true when intake Q7 (participants) is `true`,
    or Q7 is unknown for an empirical Q5 kind (`empirical_quantitative`,
    `empirical_qualitative`, `mixed`).
  - `has_ethics_approval(root)` — a recorded approval with `gate: GE`,
    `actor_role: ethics_committee`, an approve decision, **and** a document.
    Synthetic participants never satisfy this (FR-59).
  - `ethics_gate_finding(root)` — `lifecycle.ethics_missing` blocker (A6) when
    ethics is required but not approved; `None` otherwise.
- **`rh ethics check`** — read-only; `blocked` (exit 3) when A6 is barred, else
  `ok`; reports whether ethics is required and whether A6 is permitted.
- i18n en+uk.

The GE gate definition and the external `rh gate record GE --actor-role
ethics_committee --document …` path already exist (M1/M3-06); recording GE stays
human-only there.

## Not in this card

Wiring `ethics_gate_finding` into the A6 stage transition (refusing to start A6)
is M3-08, alongside the other stage-transition enforcement; this card provides
the predicate and the read-only check.

## Tests

`tests/unit/lifecycle/test_ethics.py`: requires-ethics rules (participants
true/false/unknown×kind), approval needs committee + document, finding present
when required-and-unapproved and cleared once GE is recorded, no finding when not
required. Full `rh-dev` gate green.
