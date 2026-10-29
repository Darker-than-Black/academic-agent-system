# Thesis Layer

**Milestone(s).** M4. Uses the unit tree (M1), summaries and context packs (M2), multilevel review and overlap (M3).

**Requirements.** FR-15a, FR-15b, FR-50; NFR-04; ADR-011 rev.2 p.4, ADR-012, ADR-018, ADR-019.

## Purpose

Give a dissertation what an article does not need: a thesis index, a publication plan counted by the regulator's rules, an introduction with all mandatory elements, a contribution map, conclusions that stay within the chapters, volume counted in characters and author's sheets, and manual import of the author's own published text with an overlap check. A thesis never reads article folders (ADR-011 rev.2).

## Owned files

| Path | Content |
|---|---|
| `thesis/index.json` (thesis folder) | Research question, aim, tasks → units (chapters / subsections) → publications (bib keys) |
| `thesis/pubplan.json` | Publications as bibliographic records with counting attributes |
| `thesis/contribution-map.json` | Task ↔ unit ↔ conclusion; novelty item ↔ unit ↔ publication |
| `thesis/volume.json` | Last volume count per unit and document |
| `thesis/imports/<id>.json` | Records of imported own text |
| `harness/rulepacks/ua-mon-phd/` | Counting, self-plagiarism exclusion, introduction elements, volume limits (sources checked; `[Н?]` → max `major`) |
| `harness/rulepacks/ua-mon-thesis-format/` | Formatting per наказ МОН № 40 (export profile, what counts in volume) |

## Commands

| Command | Behaviour |
|---|---|
| `rh thesis index show\|set …` | Edit the index through commands (controlled file) |
| `rh pubplan add --bib KEY …` / `rh pubplan check` | Counting per rule pack; each rule shown in the result |
| `rh volume [--unit U]` | Characters with spaces and author's sheets (1 а. а. = 40 000 characters) per rule pack |
| `rh contribution-map check` | Deterministic map checks + integration-critic request |
| `rh import own-text FILE --into U --bib KEY` | Manual import into a unit; overlap check and citation mandatory |

## Data contracts

| Record | Fields |
|---|---|
| Thesis index | `{question, aim, object, subject, tasks[{id TK-N, text, units[]}], novelty[{id NV-N, text, units[], publications[]}]}` |
| Publication | `{bib_key, title, venue{title, issn[]}, year, issue_id?, authors_count, author_position?, status: planned\|submitted\|accepted\|published, venue_status_check_id?, self_plagiarism_flag: none\|suspected\|confirmed, counts_as?: computed}` |
| Pubplan result | `{rule_stack_ref, items[{bib_key, counts_as, rules_applied[]}], total, required_min, result: pass\|fail\|unknown, findings[]}` |
| Volume | `{unit_id, chars_with_spaces, excluded[{kind: table_full_page\|figure_full_page\|references\|appendix, chars}], counted_chars, author_sheets}` |
| Own-text import | `{source_bib_key, source_sha256, target_unit, imported_at, overlap_run_id, citation_present: bool}` |

## Rules (data in `ua-mon-phd`; values verified in M4-01 against primary texts)

| Key | Content | Evidence level now |
|---|---|---|
| `pubplan.min_publications` | ≥ 3 publications | [Н] постанова КМУ № 44 |
| `pubplan.coauthor_weight` | > 2 co-authors → 0.5 (with exceptions) | [Н] |
| `pubplan.one_per_issue` | ≤ 1 article per issue counts | [Н?] → `major` until verified |
| `pubplan.self_plagiarism_exclusion` | A publication with self-plagiarism does not count | [Н?] постанова № 1240 → `major` until the primary text is read |
| `pubplan.venue_status_on_date` | Venue in the Перелік / index on the publication date | [Н] |
| `thesis.intro_elements` | актуальність, мета, завдання, об'єкт, предмет, методи, новизна, теоретичне і практичне значення, апробація, публікації | [Н] / to verify |
| `thesis.volume_limits` | Main-text volume in а. а. from the Порядок / ОНП | [Н?] |
| `thesis.volume_exclusions` | Full-page tables and figures, references, appendices not counted | [Н] наказ МОН № 40 |

## Behaviour

- **Publication plan (FR-15a).** Deterministic counting; each item lists which rules applied; total vs minimum; unknown venue status → `unknown`, never `pass`.
- **Introduction (FR-15b p.1).** Each required element must exist as a marked block (heading, or an `<!-- rh:element=… -->` anchor [P]) in the introduction unit; missing → finding with location.
- **Contribution map (p.2).** Every task has ≥ 1 unit and a conclusion; every novelty item has a unit and a publication; gaps → findings (D20).
- **Conclusions (p.3).** Chapter conclusions and general conclusions do not exceed the content of their chapters: semantic check by the chapter / integration critic (`review.md`), plus a deterministic pre-check that every conclusion paragraph references ≥ 1 claim or unit.
- **Formatting and volume (p.4, FR-50).** Volume counter over Markdown with exclusions; targets per unit come from briefs; out of range → finding at document and unit level (T55).
- **Import own text (p.5).** Imported text → overlap check against `_author/corpus/` and citation check; missing citation → finding (D21).

## Invariants

1. The thesis folder never reads other object folders; publications are bib records.
2. `unknown` counting inputs never produce `pass`.
3. Rules with secondary evidence cannot be blockers.

## Checks

| Check ID | Kind | Severity | Rule source |
|---|---|---|---|
| `thesis.pubplan_below_min` | D | blocker for T7 | `ua-mon-phd` |
| `thesis.intro_element_missing` | D | major | FR-15b, D20 |
| `thesis.task_without_unit` / `thesis.novelty_without_publication` | D | major | FR-15b, D20 |
| `thesis.conclusion_beyond_chapter` | S | major | FR-15b, D17 |
| `thesis.volume_out_of_range` | D | major | FR-50 |
| `thesis.unit_over_target` | D | minor | FR-50 |
| `thesis.import_uncited` | D | blocker | FR-15b, D21 |

## Reuse

None adopted; the OpenDraft thesis flow is an idea only (registry §3).

## Tests

| Test | Fixture | Milestone |
|---|---|---|
| T32 | F5a | M4 |
| T54 | F7 (D20, D21) | M4 |
| T55 | F7 | M4 |
| T15 (performance, ≈400 k chars, p95 < 10 s) | F7 scaled | M4 |

## Open points

- [?] Primary text of постанова КМУ № 1240 and current Порядок / ОНП volume limits — read in M4 before `verified`.
- [P] Anchor format for introduction elements: headings first, HTML-comment anchors as fallback.
- [?] Which of УДУ's local rules (ОНП, regulation on AI) apply — the author supplies them.
