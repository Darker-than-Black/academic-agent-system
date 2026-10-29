# Gates and lifecycle

**Milestone(s).** M1 (cards M1-10, M1-11: G0, stage model, status, `start` / `continue`); M3 (G1–G3 and GE enforcement, SubmissionRecord / PublicationRecord, `revise` / `reviews` routing, autonomy enforcement — see `integrity.md`).

**Requirements.** FR-28, FR-33, FR-35, FR-41; ADR-011 rev.2 p.5, ADR-015; NFR-03, NFR-09.

**Purpose.** Know where each article or thesis is, what blocks it, what the next action is, and make sure every human decision is recorded only by the human, with a clear explanation of what he is deciding.

**Owned files.** Object: `object.json` → `stages`, `approvals/requests/AR-*.json|md`, `approvals/approvals.jsonl`. Harness: `harness/gates/*.yaml`, `research_harness/{gates,lifecycle}/`, `lifecycle/{article,thesis}_stages.yaml`.

**Commands.** `rh start`, `rh continue`, `rh status`, `rh gate request|explain|record|list`; M3: `rh revise`, `rh reviews`.

**Data contracts.** 02 §4.2 (stages, gates), §5.7 (stage contracts), §9.3 (gate definitions, briefings, requests, approvals); 03 §3 (status report).

**Invariants.**
1. A stage becomes `completed` only when its DoD checks pass; `blocked` always has a reason and a next action (02 §2).
2. Approvals are written only through the human channel (TTY + confirmation code, `RH_AGENT_SESSION` unset); agents can only request (FR-35, ADR-015 p.2).
3. An approval binds to a snapshot hash; any later content change invalidates it for the new snapshot (02 §6).
4. External roles require a document (FR-35).
5. Every request has a briefing in the author's UI language (decision 2026-10-29).
6. Status always gives exactly one next action and names who must do it (NFR-09).
7. A16 is `waiting`, never `completed`; no reminders or status checks without the author's request (FR-34, ADR-015).

**Checks.**

| ID | Kind | Severity | Source |
|---|---|---|---|
| `gate.missing` (stage needs gate, none valid) | D | blocker | 02 §4.2 |
| `gate.stale` (approval for older snapshot) | D | blocker | 02 §6 |
| `gate.external_without_document` | D | blocker | FR-35 |
| `gate.non_human_channel` | D | blocked (exit 3) | 02 §9.3 |
| `stage.blocked_without_reason` | D | blocker | 02 §2 |
| `briefing.incomplete` | D | major | 02 §9.3 |

**Reuse.** StageContract (#19) via `state.md`.

**Tests.** T29a, T37, T44 (M1 parts); T35, T36 and T29a records in M3.

**Open points.** [?] Whether commands run from inside Claude Code count as the author's terminal is checked in M1-14 (H12).
