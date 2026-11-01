# M3-05 — Disputes and finding resolution

> Milestone M3a. Module `review.md`. Requirements FR-23, FR-35.
> Tests T23, T13. Depends on M3-02. Base `main`.

## Goal

A finding can be resolved only by the author (the gate channel rule), and a
critic/analyst disagreement runs a bounded dispute that never auto-passes.

## What this card delivers

- **`findings/index.py`** — the finding index (`findings/index.jsonl`): `add`,
  `list_findings(status?)`, `resolve(decision, reason, by)`. Status is
  open/accepted/rejected/fixed/unresolved; resolutions are append-only; **reject
  requires a reason** (T13).
- **`review/disputes.py`** + **`schemas/dispute.schema.json`** — dispute records
  (`reviews/disputes/D-N.json`): `open_`, `add_evidence` (one cycle per call,
  refused once closed or at `max_cycles`, default 2), `close` to
  `resolved_by_author` or `unresolved`. A dispute never auto-resolves to a pass
  (T23).
- **CLI**:
  - `rh findings list [--status]` and `rh findings resolve F-ID --decision
    accept|reject|fixed [--reason]` — registered on the shared `findings`
    command (owned by the synthesis CLI, which delegates list/resolve here so
    the command stays one namespace). Resolve is **human-only**: in an agent
    channel (`RH_AGENT_SESSION`, or no TTY) it writes nothing and returns a
    resolution request with `next_actions: who=author`, exit 3 (H14).
  - `rh dispute open --claim --finding [--max-cycles]`,
    `rh dispute add-evidence D-ID --by analyst|critic --argument --evidence…`,
    `rh dispute close D-ID --status … [--author-decision]`. Closing to
    `resolved_by_author` is human-only (same guard); `unresolved` escalation is
    allowed in any channel.

## Not in this card

Review `submit` does not yet auto-populate `findings/index.jsonl` from a review's
findings (wiring lands with the check-run/report card); for now findings are
added via `findings.add`. The briefing text for a resolution request (finding +
evidence + consequence) reuses the gate briefing style and is minimal here.

## Tests

`tests/unit/findings/test_index.py` (add/list/resolve, reject-needs-reason,
append-only, unknown id), `tests/unit/review/test_disputes.py` (cycle cap,
no-auto-resolve, close states), `tests/integration/test_resolution_cli.py`
(human-only block on resolve and on close→resolved_by_author; unresolved allowed;
dispute open/add). dispute schema examples. Full `rh-dev` gate green.
