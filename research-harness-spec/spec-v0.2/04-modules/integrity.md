# Integrity

**Milestone(s).** M3 (all parts below); M4 adds thesis-level use of the overlap check (thesis.md).

**Requirements.** FR-12 (verified), FR-16, FR-17, FR-19, FR-19a, FR-30, FR-32, FR-37, FR-51, FR-53 (status and AI statement part); NFR-06, NFR-11, NFR-12, NFR-14; ADR-012 p.6, ADR-014 p.4–5, ADR-017, ADR-018.

Mode handling, records, locked sections, autonomy enforcement and GE are in `lifecycle-records.md` (split from this module).

## Purpose

Keep the author's work honest and safe before anything leaves the harness: detect overlap with his own texts, document AI use from real provenance data, check rights of assets and the status of the target venue, enforce verified-export conditions, keep secrets and foreign material out of git, treat injected instructions as data, and help the author avoid his own typical errors while preserving his voice. The harness never hides AI use and never inserts errors (decision 2026-10-28, `03-requirements-v0.2.md` §9).

## Owned files

| Path (object folder) | Content |
|---|---|
| `integrity/overlap/<run-id>.json` + `report.md` | Overlap report |
| `integrity/ai-use.json` | AI-use record (FR-32) |
| `integrity/ai-statement.<lang>.md` | Draft AI-use statement per rule pack, generated from provenance |
| `assets/registry.json` | Asset registry (FR-17) |
| `venue/checks/<check-id>.json` | Venue status evidence (FR-37) |
| `export/verified-<snapshot>/manifest.json` | Verified export manifest (export layout itself: docx.md) |

| Path (workspace / harness) | Content |
|---|---|
| `_author/corpus/` + `index.json` | Overlap corpus (02 §3.2) |
| `_author/style/<lang>/profile.yaml` | Style profile per language (FR-19) |
| `_author/errors-profile.yaml` | Chosen typical-error categories (FR-51) |
| `harness/rulepacks/core/rules/errors-catalog.yaml` | Catalogue of typical errors (data; texts uk + en) |
| `harness/rulepacks/ua-mon-phd/`, `ua-fahove-b/`, `scopus-indexed/` | Overlap thresholds, AI-statement requirements, venue rules (written in M3 cards; sources checked against primary texts; `[Н?]` rules capped at `major`) |
| `harness/src/research_harness_dev/repo_check.py` | PR check (T41); also exposed as `rh repo check` |

## Commands

| Command | Behaviour |
|---|---|
| `rh overlap [--unit U] [--against corpus]` | Deterministic overlap of current text with `_author/corpus/` |
| `rh ai-use show` / `rh ai-use statement --lang L` | Record and draft statement from paragraph provenance |
| `rh asset add PATH --origin … --rights …` / `rh asset list` | Asset registry |
| `rh venue check [--venue ISSN] [--date YYYY-MM-DD] --evidence FILE\|URL` | Records venue-status evidence with date and resource |
| `rh export --mode verified` | Conditions below; export mechanics in docx.md |
| `rh repo check [--staged]` | PR check; `rh-dev check` calls it |
| `rh style profile build --lang L` / `rh style profile propose` / `rh style profile accept PROPOSAL-ID` | FR-19: built from corpus; proposals from author edits applied only after the author accepts (human channel) |
| `rh errors profile choose` / `rh errors check [--unit U]` | FR-51 |

`rh asset`, `rh style`, `rh errors` are new noun groups (not in 03-cli §2.8).

## Data contracts

| Record | Fields |
|---|---|
| Overlap match | `{unit_id, paragraph_id?, char_start, char_end, corpus_doc_id, corpus_locator, shingle_size, overlap_words, overlap_ratio, cited: bool, severity}` |
| Overlap report | `{run_id, snapshot_id, corpus_index_sha256, rule_refs[], method: {normalization, shingle_size, min_fragment_words}, matches[], limitations[]}`; empty corpus → `result: unknown` with consequence |
| AI-use record | `{object_id, entries[{stage, role, model_id, model_tier, purpose, units[], at}], provenance_shares: {author, agent_edited_by_author, agent}, generated_from: [model-calls ref, paragraph-map refs with sha256]}` |
| Asset | `{id AS-NNN, path, sha256, kind: figure|table|image|other, origin: own_generated|own_data|third_party, source_ref?, license?, rights_status: own|licensed|permission_documented|unknown, permission_doc?{path, sha256}, generated_from_rows?[]}` |
| Venue check | `{id, venue{title, issn[]}, resource: scopus_sources|mjl|doaj|ua_perelik|journal_site, query_date, status_on_date: {date, value: included|not_included|unknown}, evidence{url?, file?, sha256?}, checked_by, rule_refs[]}` |
| Style profile | `{lang, version, built_from[corpus refs], features{sentence_length, voice, connectives, preferred_terms, banned_phrases[]}, accepted_proposals[]}` |
| Errors profile | `{chosen[{category_id, note?}], voice: I|we|impersonal, version}` |

## Parts

### Overlap with own texts (FR-30, ADR-018)

- Corpus = `_author/corpus/` only (ADR-011 rev.2); no other object folder is read.
- Normalization: NFC, lowercase, punctuation stripped, Ukrainian apostrophe variants (’ ' ʼ) unified, hyphen variants unified; Latin and Cyrillic look-alike letters mapped in a copy used only for matching.
- Method: word shingles (default 8 words), merged into fragments; report fragments ≥ `min_fragment_words` (default 25). Thresholds and severities come from rule packs (`ua-mon-phd`), not code.
- `cited` = the fragment's unit cites the corpus document's bib key within the same or adjacent paragraph. Not cited → higher severity (T31).
- Limitation always stated: paraphrase without textual overlap is not detected; this is not the official university check (FR-16).

### AI-use record and statement (FR-32, FR-53)

- Built only from data: `.rh/model-calls.jsonl` and paragraph provenance (claims-text.md). Never from the agent's self-description.
- Draft statement: template per rule pack (journal / venue class / regulator), in the manuscript language; lists stages and purposes, share of paragraphs by origin. It is a draft; what to submit is the author's decision (FR-16).
- Missing record at export → finding (T34). Instructions to hide AI use (e.g. a style rule "make detectors not recognize AI") are not applied and produce a finding (N4, T47).

### Asset registry (FR-17)

Final (verified) export is blocked for a `third_party` asset without `licensed` or `permission_documented` status. Figures generated from result rows are `own_generated` and list their rows (analysis-sandbox.md).

### Venue check (FR-37)

Status is evaluated **on the date that matters** (submission date by default; rule pack may say publication date). Evidence: Scopus Sources (coverage years; no active/discontinued label — status derived from coverage years, `06-research-agent.md` §3.1), Clarivate MJL, DOAJ, the Ukrainian Перелік (наказ МОН № 928, valid 1.06.2026–1.06.2029). No evidence → `unknown` (D14, T39). Manual mode: the agent gives the author the query; the author saves the page or screenshot; `rh venue check --evidence` records hash and date.

### Verified export conditions (FR-12)

All must hold, checked in code: G3 approval valid for the current snapshot; no open blocker finding; rule packs of layers 3–6 current (`review_after` not passed); every required check `pass` (none `unknown`); review coverage complete for material claims; AI-use record present; asset rights resolved; venue check present and current for the target date. Any failure → exit 3 with the list.

### Repository check (T41, NFR-11)

Blocks a commit / PR containing: files under `**/holdout/**`; any file whose hash is in `harness/evals/holdout.lock.json`; foreign full texts (paths of 01 §5 and PDFs not marked `own`); files marked `private`; secrets (patterns for API keys of OpenAlex, CORE, Semantic Scholar, OpenAI, Anthropic, generic `*_KEY=`/`Bearer`, private keys); `.env`, `*.local.yaml`. Output lists every offending path and reason.

### Prompt injection (T14, D10)

Source text is passed to models only inside clearly delimited data blocks with the instruction that it is data. A deterministic scan flags imperative patterns addressed to an assistant ("ignore previous", "send", "reveal", URLs with tokens) in imported text → finding with locator; the content is never executed, and secrets are never placed in any context pack.

### Typical-errors profile (FR-51)

The catalogue (rule-pack data) lists categories: voice and person (I / we / impersonal mixing), calques and bureaucratese, terminology, argumentation, formatting, structure. The author chooses his categories once (intake or on request). `rh errors check` reports findings with proposed fixes, higher priority for chosen categories and for the author's own edits and imported `.docx`. Deterministic where possible (voice markers, listed calques); semantic otherwise. **The system never introduces errors into any version or export** (T56).

### Style profile (FR-19, FR-19a)

Built from the author's corpus per language. Stylization must not change numbers, citations, qualifiers or limitations: a deterministic invariant check compares these before/after (T19, MY invariants 100%). Proposals derived from the author's edits are applied only after he accepts them.

## Invariants

1. No other object folder is read by any integrity check.
2. AI-use data comes from logs and provenance only.
3. No code path inserts deliberate errors or removes AI-use traces.
4. Verified export re-checks every condition itself; it never trusts a cached PASS.
5. `unknown` (empty corpus, missing venue evidence, expired rule) never passes.

## Checks

| Check ID | Kind | Severity | Rule source |
|---|---|---|---|
| `integrity.overlap_uncited` | D | per rule pack (default major; blocker for thesis counting) | ADR-018, `ua-mon-phd` |
| `integrity.overlap_cited` | D | info / minor | ADR-018 |
| `integrity.overlap_corpus_empty` | D | unknown + major | ADR-018 |
| `integrity.ai_use_missing` | D | blocker for verified export | FR-32 |
| `integrity.ai_concealment_request` | D | major | N4 |
| `integrity.asset_rights` | D | blocker for verified export | FR-17 |
| `integrity.venue_status` | D | blocker if `not_included`, unknown if no evidence | FR-37 |
| `integrity.rules_expired` | D | blocker for verified export | NFR-12 |
| `integrity.style_invariants` | D | blocker | FR-19a |
| `integrity.prompt_injection` | D + S | major | T14 |
| `integrity.chosen_error` / `integrity.error` | D / S | minor (chosen: major) | FR-51 |
| `repo.forbidden_path` / `repo.secret` / `repo.holdout` | D | blocker | NFR-11, T41 |

## Reuse

| # | Origin (short SHA) | License | Mode | Change | Acceptance test |
|---|---|---|---|---|---|
| 11 | OPM `skills/coauthor-engine/SKILL.md` (`160df4d`) | MIT | adapt | CRediT + human/AI split feeds AI-use record, not free text | T34 |
| 36 | OpenDraft `prompts/05_refine/entropy.md` | MIT | **reject** | — | N4 in T47 |
| 35 | OpenDraft `prompts/05_refine/voice.md` | MIT | idea only | Style profile is data edited by the author | T19 |

## Tests

| Test | Fixture | Milestone |
|---|---|---|
| T11 (verified) | F4-W, F5b | M3 |
| T14 | F4-W, F4-H, F5c | M3 |
| T17 | F4-W figures | M3 |
| T19 | F4-W + F6 | M3 |
| T31 | F5a + corpus | M3 |
| T34 | F4-W | M3 |
| T39 | F5g, D14 | M3 |
| T41 | F5c | M3 |
| T47 (baseline, N4) | F6 | M3, M5 |
| T56 | F4-W + F5d | M3 |
| T58 (status, statement) | F4-W + F5d | M3 |

## Open points

- [P] Default shingle size 8 and minimum fragment 25 words — tune on F7 and the author's corpus in M3; final values live in `ua-mon-phd`.
- [?] Access method to the Ukrainian Перелік (search page or downloadable list) — check in M3.
- [?] Retraction data terms of use (registry #17) belong to sources-library.md; not used here.
