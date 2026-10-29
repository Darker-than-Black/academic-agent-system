# Intake, materials, rule packs

**Milestone(s).** M1 (cards M1-08, M1-09: engine, intake, materials, packs `core`, `article`, `thesis`); M2 (card M2-11: packs `literature-narrative`, `conceptual`, `ua-fahove-b` format part); M3 (venue-class and journal checks, freshness before G3 — see `integrity.md`); M4 (`ua-mon-phd`, `ua-mon-thesis-format` — see `thesis.md`); M6 (`ml-empirical` — see `ml.md`).

**Requirements.** FR-01, FR-26, FR-27, FR-36, FR-44, NFR-12, NFR-15; ADR-012.

**Purpose.** Collect the context of each article or thesis once (intake → G0), register what the author provided, and turn country / venue / institution requirements into versioned data that checks can rely on.

**Owned files.** Object: `intake/answers.json`, `intake/summary.md`, `materials/manifest.json`, `materials/private/**` (gitignored), `profiles/resolved-stack.json`. Harness: `harness/intake/questions.yaml`, `harness/rulepacks/**`, `research_harness/{intake,materials,rules}/`.

**Commands.** `rh intake questions|answer`, `rh materials add|list`, `rh rules resolve|lint|freshness`.

**Data contracts.** 02 §8 (packs, rules, composition, freshness, resolved stack), §9.1 (questions, answers), §9.2 (materials manifest).

**Invariants.**
1. Unknown stays `unknown`, always with a consequence shown to the author (FR-01, FR-26).
2. A fact known from the author level or a previous intake is never asked again; it is shown as prefilled for confirmation (FR-44, NFR-15).
3. Core intake ≤ 10 questions (NFR-15).
4. No national, venue or institution rule exists in code or prompts — only in packs (ASR-06).
5. A rule without a source is not a rule; a `secondary` source caps severity at `major`; an expired rule makes dependent checks `unknown` (02 §8.3–8.4).
6. Core rules cannot be overridden.
7. Materials marked private never enter git; foreign PDFs are recorded by hash and locator only (NFR-11).

**Checks.**

| ID | Kind | Severity | Source |
|---|---|---|---|
| `intake.required_missing` | D | blocker for G0 | 02 §9.1 |
| `intake.unknown_without_consequence` | D | blocker | FR-26 |
| `rules.conflict_same_layer`, `rules.conflict_incomparable` | D | blocker at A0 | 02 §8.3 |
| `rules.core_override_attempt` | D | major | 02 §8.3 |
| `rules.expired`, `rules.not_yet_valid` | D | blocker for verified export / info | 02 §8.4 |
| `rules.secondary_capped` | D | info | ADR-012 p.5 |
| `materials.doi_malformed`, `materials.duplicate_linked` | D | minor / info | FR-36 |
| `materials.private_tracked` | D | blocker | NFR-11 |

**Rule packs by milestone.**

| Pack | Layer | Milestone | Content | Source status |
|---|---|---|---|---|
| `core` | 0 | M1 | Harness invariants (no invented sources, data, approvals; unknown ≠ pass; provenance; AI-use record; human-only external actions) | Own requirements, `primary` |
| `article`, `thesis` | 1 | M1 | Allowed unit kinds and depth; required parts | Own requirements |
| `literature-narrative` | 2 | M2 | Protocol fields; every review claim → excerpt; access level visible; must not be called systematic | `02-lifecycle.md` §4 |
| `conceptual` | 2 | M2 | Every premise from a source or marked assumption; definitions used consistently | `02-lifecycle.md` §4 |
| `ua-fahove-b` (format part) | 4 | M2 | Abstracts UA + EN, keywords, ORCID, reference style ДСТУ 8302:2015 as default for the class with journal override, AI-use statement required where the journal has an AI policy | To verify against Наказ МОН № 928 criteria and sample journal guidelines; `secondary` until checked |
| `ua-fahove-b` (status part), `scopus-indexed` | 4 | M3 | Inclusion on date, indexing evidence | See `integrity.md` |
| `ua-mon-phd`, `ua-mon-thesis-format` | 3, 6 | M4 | Publication counting, self-plagiarism exclusion, thesis structure and volume | See `thesis.md` |
| `ml-empirical` | 2 | M6 | ML protocol | See `ml.md` |

**Reuse.** OpenDraft #32 dedup (M1-09). Details: `06-reuse-adoption.md`.

**Tests.** T01, T26, T27, T28, T29, T38; fixtures F5a, F4-W metadata.

**Open points.** [P] Which journal(s) the author targets for the first case decides whether a `journal:<ISSN>` pack is written in M2 or M3 — asked in M2 (question for the author in `07-milestones/M2.md`).
