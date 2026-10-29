# Summaries, map, glossary, context packs

**Milestone(s).** M2 (cards M2-08, M2-09). Multilevel review that consumes them — M3 (`review.md`).

**Requirements.** FR-47, FR-48, NFR-16; ADR-019 p.3–4, ADR-010 rev.2.

**Purpose.** Let agents work on a 200-page thesis without loading it: every unit has a summary tied to its text hash, the document has a map and a glossary, and every agent call gets a context pack assembled by the CLI within a stated budget.

**Owned files.**

| Path | Content | Class |
|---|---|---|
| `<unit>/summary.md` | Front matter: `text_sha256`, `deterministic: {...}`, `semantic: {...}`, `produced_by`; body: human-readable summary | controlled |
| `map.md` | Generated document map: tree, per unit — title, volume, main thesis, key claim IDs, status, freshness | controlled |
| `glossary.md` | Terms: `term`, `definition`, `source` (excerpt / premise / author), `aliases[]`, `first_unit`, language | content (author and agent on request) + validated |
| `context/packs/<pack-id>.json` | Manifest of each pack built (not the content) | controlled |

Harness: `research_harness/summaries/{deterministic.py, semantic.py, map.py, glossary.py}`, `research_harness/context/{pack.py, budget.py}`.

**Commands.** `rh summary build U [--deterministic-only]`, `rh summary set U --file F` (store a semantic summary produced by the summarizer role), `rh summary check`, `rh map build`, `rh glossary add|check`, `rh context pack U --role R [--budget N] [--out F]`.

**Data contracts.**

Deterministic summary part (CLI, no LLM — FR-47): `{text_sha256, chars_with_spaces, author_sheets (chars / 40 000), paragraphs, cite_keys[], numbers[{value, unit?, paragraph}], terms_used[] (from glossary), cross_refs[{target_unit, resolved: bool}], placeholders, claims[]}`.

Semantic summary part (summarizer role, `fast` tier; checked by the unit critic in M3): `{main_thesis, key_claims: [C-id], open_questions[], language}` — at most 150 words of prose plus IDs [P].

Context pack manifest: `{id, unit_id, role, built_at, snapshot_id, budget: {limit, used, unit: tokens_estimate}, items: [{ref, sha256, kind, size_estimate, reason}], excluded: [{ref, reason}], status: ok|over_budget}`.

Default pack composition by role (FR-48; budgets are config, initial values [P]):

| Role | Always | If present | Never |
|---|---|---|---|
| writer (unit) | brief, `map.md`, glossary, parent chapter summary, neighbour unit summaries, evidence for planned claims, style profile version | author's dictation for the unit | full text of other units |
| unit critic | full unit text, brief, evidence for the unit's claims | glossary | writing history, other units' text |
| chapter critic (M3) | full text of the chapter's units, chapter brief | glossary | writing history |
| integration critic (M3) | `map.md`, all summaries, CLI full-text check results | full text of units named in findings (sampled reading) | writing history |
| researcher | protocol, search plan, matrix, positions, gaps | relevant excerpts | manuscript text |
| summarizer | full unit text | glossary | other units |

Token size is estimated as `ceil(chars / 3.5)` for Ukrainian and `ceil(chars / 4)` for English [P]; the estimate method and value are recorded in the manifest.

**Invariants.**
1. A summary is valid only for the text hash it records; any text change makes the unit summary, its chapter summary and `map.md` stale (FR-47, T51).
2. Integration-level work never runs on stale summaries (FR-47).
3. A pack over budget is an error with an explanation and the list of items; never silent truncation (NFR-16, T52).
4. The orchestrator never receives the full text of more than one unit: `rh context pack` refuses role `orchestrator` with more than one unit text, and status / map give it only summaries (NFR-16, ADR-010 rev.2).
5. Every agent call over the document has a pack manifest; the manifest ID is logged with the model call (FR-48).
6. Glossary terms are checked across all units by the CLI (term used with a different definition, or a defined term missing from usage) — full-document check, cheap and deterministic.

**Checks.**

| ID | Kind | Severity | Source |
|---|---|---|---|
| `summary.stale`, `map.stale` | D | blocker for integration review and verified export | FR-47 |
| `summary.semantic_missing` | D | major | FR-47 |
| `pack.over_budget` | D | error (exit 3) | NFR-16 |
| `pack.orchestrator_full_text` | D | refused (exit 3) | NFR-16 |
| `pack.unlogged_call` | D | major | FR-48 |
| `glossary.term_undefined`, `glossary.alias_conflict` | D | minor / major | ADR-019 p.5 |
| `crossref.unresolved` | D | major | ADR-019 p.5 |
| `summary.faithfulness` | S | advisory (unit critic, M3) | FR-47 |

**Reuse.** None (own).

**Tests.** T51, T52 (M2); T53 consumes these in M3; fixture F7.

**Open points.** [P] Initial budgets: writer 40k tokens, unit critic 60k, integration critic 80k — to be tuned on F7 in M2-15 and recorded in config.
