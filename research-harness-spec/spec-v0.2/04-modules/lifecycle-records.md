# Lifecycle Records, Modes and Autonomy

**Milestone(s).** M3. (Stage model, status and `start`/`continue` routing are M1 — gates-lifecycle.md.)

**Requirements.** FR-21, FR-28 (records), FR-31, FR-33 (enforcement), FR-34, FR-41 (`revise`, `reviews`), FR-35 (external approvals for GE); ADR-011 rev.2 p.5–6, ADR-015.

## Purpose

Make the article a long-lived object: record submissions and publications, support returning in `revise` and `respond_to_reviewers` modes without touching locked text, enforce the chosen autonomy level and the ethics gate in code, and never act on an article without the author's request.

## Owned files

| Path (object folder) | Content |
|---|---|
| `records/submissions.jsonl` | SubmissionRecord |
| `records/publications.jsonl` | PublicationRecord |
| `reviews/external/<round>/` | Reviewers' comments as received (text / .docx), response table |
| `manuscript/original/` | Imported original manuscript for `revise` (read-only after import) |
| `manuscript/diffs/` | Diffs per version |
| `locks.json` | Locked units with reason and who locked |
| `ethics/` | GE documents (`stored=false` if private) |

## Commands

| Command | Behaviour |
|---|---|
| `rh revise [--from FILE.docx\|.md] [--scope U…]` | Short intake (mode `revise`), import original (docx.md), change plan, locks outside scope proposed for the author's confirmation |
| `rh reviews add FILE` / `rh reviews table` / `rh reviews respond` | Mode `respond_to_reviewers` (A14): comment → action → location → evidence → response; each comment closed or argued |
| `rh lock U --reason R` / `rh unlock U` | Lock / unlock units; unlock is human-only (TTY rule) |
| `rh record submission --venue … --date … --manuscript-id …` / `rh record publication --doi … --issue … --date … --license …` | Human-only records (they describe external facts); tag snapshots `submitted:<date>` / `published` |
| `rh autonomy set step\|gates\|batch` | Changes object autonomy; human-only |

`rh lock`, `rh unlock`, `rh record`, `rh autonomy` are new (not in 03-cli §2.8).

## Data contracts

| Record | Fields |
|---|---|
| SubmissionRecord | `{id SUB-NN, venue{title, issn[]}, date, manuscript_id?, snapshot_id, manifest_sha256, g3_approval_id, channel_note}` |
| PublicationRecord | `{id PUB-NN, submission_id, doi?, volume?, issue?, pages?, date, license?, url?, snapshot_id (version of record), proof_diff_ref?}` |
| Reviewer comment | `{id RC-NN, round, reviewer, text, location_hint?, action: accept|partial|decline, response, changed_units[], evidence_refs[], status: open|closed}` |
| Lock | `{unit_id, reason, locked_by, at}` |

## Behaviour

- **Modes (FR-21).** `create` and `extend` start at A0 → A1 / A2 / A6 (02-lifecycle §5). `revise`: A0 short intake → import → agreed scope → required stage. `respond_to_reviewers`: A14. `extend` is SHOULD. Original and every diff are kept.
- **Locked units.** Any write to a locked unit — by agent or by `rh` — fails with exit 3 (T21), even when the author asks; he must unlock first (02 §5.6 rule 4).
- **Records.** SubmissionRecord requires a valid G3 for the submitted snapshot; tagged snapshots are frozen for migrations (NFR-10).
- **Long-lived object (FR-34, ADR-015 p.3–4).** A16 state is `waiting`. No command schedules reminders, status polling or proposals. On return, `rh continue` shows history and re-resolves rule packs (rules may have changed); nothing changes until the author asks.
- **Autonomy (FR-33).** `step`: `rh` returns `next_actions` with `who: author` after each stage completes; `gates`: only at gates and human decisions; `batch`: questions are queued in `next_actions` and stages continue until a gate. On every level G0–G3, GE, finding resolutions and external actions require the author — enforced in `rh` (gate and resolution commands are human-only), not by prompts (ASR-04).
- **GE (FR-31).** If intake has `participants=true` (or `unknown` for an empirical study kind), A6 is blocked until an external approval with `actor_role: ethics_committee` and a document exists (T33). Synthetic participants never satisfy anything (analysis-sandbox.md, FR-59).

## Invariants

1. No change to an object without a command the author asked for or a task he started.
2. Locked units are immutable until unlocked by a human.
3. Records of external facts are written only by a human.
4. Earlier snapshots, submissions and publications are never rewritten.

## Checks

| Check ID | Kind | Severity | Rule source |
|---|---|---|---|
| `lifecycle.locked_write` | D | blocker | FR-21 |
| `lifecycle.submission_without_g3` | D | blocker | FR-28 |
| `lifecycle.ethics_missing` | D | blocker (A6) | FR-31 |
| `lifecycle.reviewer_comment_open` | D | major (blocks new G3) | 02-lifecycle A14 |
| `lifecycle.autonomy_gate_skip` | D | blocker | FR-33 |

## Reuse

| # | Origin (short SHA) | License | Mode | Change | Acceptance test |
|---|---|---|---|---|---|
| 5 | OPM `skills/review-engine/SKILL.md`, `commands/respond-reviewers.md` (`160df4d`) | MIT | adapt | Output = our reviewer-comment table; every change through `rh` with request | T21, T44 |
| 23 | AutoResearchClaw `hitl/diff_view.py` (`be4ba47`) | MIT | adapt | Unit-level diffs; used by `revise` and docx import | T21 |

## Tests

| Test | Fixture | Milestone |
|---|---|---|
| T21 | F4-W | M3 |
| T29a (records) | F5b | M3 |
| T33 | F5a | M3 |
| T35 | F5b | M3 |
| T36 | F5b | M3 |
| T44 (revise / reviews) | F5b, F5f | M3 |

## Open points

- [P] `extend` (SHOULD) is implemented in M3 only as routing to A2 / A6 with the overlap check; full behaviour after the pilot if needed.
