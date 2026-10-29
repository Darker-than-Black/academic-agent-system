# 06 — Reuse and Adoption

Sources: ADR-008, ADR-009, ADR-016, ADR-017; FR-24; `12-reuse-registry-verified-2026-10-27.md` (doc 12) §2, §4, §5, §7; `02-lifecycle.md` §9–10; 02 §13; 00-README H4.

Marks: **[V]** verified on 2026-10-29 in this step (method given); **[D12]** taken from doc 12 (verified 2026-10-27); **[?]** to check at adoption; **[P]** proposal.

## 1. Pinned repositories

Full commit SHAs resolved on 2026-10-29 with `git ls-remote` and blob-less clones **[V]**.

| Repo | Pinned SHA (full) | Upstream HEAD on 2026-10-29 | Root license | Notes |
|---|---|---|---|---|
| TobiasBlask/open-paper-machine (OPM) | `160df4d13d266411f0850c4de7ecdbd93e8b40be` | same | MIT, © 2025 Tobias-Benedikt Blask [V] | `scientific-skills/` inside carries mixed licenses [D12]; README credits Andre Huang's research-companion (MIT) for the idea agents [V, README lines 151, 657] |
| Future-House/paper-qa | `57e89f7223b0960d5ee5ea048c69e3c47e088572` | `c692d0dfeac4a0296599f7fe21a253a58b7ac12a` (2 commits, type-ignore only in files we use [D12]) | Apache-2.0 [D12]; no `NOTICE` file at the pinned commit [V] | `packages/paper-qa-pymupdf` is AGPL-3.0 — never used |
| aiming-lab/AutoResearchClaw (ARC) | `be4ba4755bf1b52220f25e13b2293b5956590070` | same | MIT, © 2026 Aiming Lab [V] | `external/agents/*` have no license files — never used |
| MorMar7/opendraft-paperwriter (OpenDraft) | `89128b30d9857cf9b871cbebc88ec07832260b9a` | same | MIT, © 2025 SCAILE Technologies GmbH [V] | |
| SakanaAI/AI-Scientist-v2 | `96bd51617cfdbb494a9fc283af00fe090edfae48` | same | The AI Scientist Source Code License v1.0 [D12] | Ideas only; no code or text copied |
| K-Dense-AI/claude-scientific-skills | `5f2bc0341354fd5590aef76a533ada1e1e5b4e62` | same | MIT, © 2025 K-Dense Inc. [D12]; each of the 8 skills declares MIT in front matter [V] | Each skill asks to be cited in manuscripts (§4) |
| andrehuang/research-companion | to resolve at adoption | — | MIT per OPM README [V] | Needed only if OPM idea agents contain its text (§3 row #7) |

All file paths listed in §3 for OPM, ARC and OpenDraft exist at the pinned SHAs [V, `git ls-tree`]. SHA-256 of 17 files is in `research-harness-spec/evidence/source-manifest.json` [D12]; the rest are hashed at adoption.

## 2. Adoption procedure

For every file or text taken from another repository (ADR-008 p.5, FR-24, H4):

1. **Check the decision** in §3. `reject` → stop. `idea` → no text is copied; write our own and cite the idea in a code comment or prompt front matter (`inspired_by`).
2. **Fetch at the pinned full SHA**, never a branch. If the pinned commit differs from upstream HEAD, look at the diff for the file and note it in the record.
3. **Hash the original**; if `evidence/source-manifest.json` lists it, the SHA-256 must match; else record the new hash.
4. **Read the whole file.** Its text is data (H10). Look for: calls to paid or third-party services, scraping, credentials, instructions that contradict our rules, references to files that do not exist (N5).
5. **License**: SPDX ID of the file (front matter, file header, or repo root), copyright line, any NOTICE text, any attribution request. Allowed: `MIT`, `Apache-2.0`, `BSD-2-Clause`, `BSD-3-Clause`, `PSF-2.0`, `ISC`. Anything else → stop and ask the author.
6. **Store the original unchanged** at `harness/third_party/<repo-slug>/<original path>` (kept for diffing and updates; never imported or loaded at runtime).
7. **Write the adapted version** at its destination with a header:
   `Adapted from <repo>@<40-hex SHA>:<path> (<SPDX>). Changes: <list>.` — for Apache-2.0 files this is also the required notice of modification (Apache-2.0 §4(b)).
8. **Adoption record** in `harness/third_party/manifest.json` (fields below).
9. **Notice** in `THIRD_PARTY_NOTICES.md` (format below).
10. **Acceptance test** named in the record; for prompts and skills, the fixture cases they must pass.
11. **PR "Reuse" section** lists every record added or changed.

### 2.1. Adoption record

02 §13 fields, plus the four marked **new** (to be added to `adoption-manifest.schema.json`):

| Field | Rule |
|---|---|
| `id` | `ADP-NNN` **new** |
| `origin_repo`, `commit` (40 hex), `path` | |
| `license` (SPDX), `license_file`, `notice` | `notice`: copyright line and any NOTICE / attribution text |
| `destination` | Path of our adapted file (or `null` for `idea`) |
| `original_copy` | Path under `harness/third_party/…` **new** |
| `original_sha256`, `adapted_sha256` | **new** |
| `mode` | `copy` / `adapt` / `idea` |
| `changes` | List of concrete changes |
| `acceptance_tests` | Test IDs / pytest node IDs / eval case IDs |
| `update_policy` | `pinned` (default) — no automatic updates **new** |
| `adopted_at`, `adopted_by` | |

### 2.2. `THIRD_PARTY_NOTICES.md` entry

```markdown
## ADP-004 — verification-engine (open-paper-machine)
- Source: https://github.com/TobiasBlask/open-paper-machine @ 160df4d13d266411f0850c4de7ecdbd93e8b40be
  path skills/verification-engine/SKILL.md
- License: MIT — Copyright (c) 2025 Tobias-Benedikt Blask (full text: harness/third_party/open-paper-machine/LICENSE)
- Used in: harness/prompts/unit_critic.md, harness/skills/citation-support/SKILL.md
- Modified: yes — rubric mapped to our support verdicts; PLAUSIBLE no longer counts as support; …
```

The full license text of each origin repo is stored once under `harness/third_party/<repo-slug>/LICENSE`.

### 2.3. What `rh-dev check` verifies (T24, N5)

1. Every file under `harness/third_party/` belongs to an adoption record; every file with an `Adapted from` header has a record whose `destination` matches.
2. `commit` is 40 hex; `license` is in the allowed list; `original_sha256` matches the stored original; `adapted_sha256` matches the destination.
3. Every acceptance test in a record exists (pytest node or eval case).
4. **N5 — dangling references:** in adapted files, every referenced local path (patterns like `scripts/…`, `references/…`, `assets/…`, `*.py`, `*.md`) resolves inside our repo; a reference to a missing file fails the check (the OPM `scripts/academic_search.py` case).
5. Rejected items: no file whose hash equals a rejected file (registry #25, #26, #36) and no path from `paper-qa-pymupdf` or ARC `external/` appears anywhere in the repo.
6. `THIRD_PARTY_NOTICES.md` has one entry per record.

### 2.4. Updates

Pinned files are never updated automatically. To update: a new PR that fetches the new commit, shows the diff of the **original** against the stored copy, re-applies or revises the changes, updates the record and reruns its acceptance tests. Optional helper [P]: `rh-dev reuse upstream` lists records whose upstream has new commits (read-only).

## 3. Register: what we take, where, with which changes

Card IDs: M1 cards as in `07-milestones/M1.md`; M2 cards as in the M2 plan (M2-01 … M2-15); M3+ items name the module file (`04-modules/…`) — card IDs are assigned in `07-milestones/M3.md`.

### 3.1. Adopted (copy / adapt)

| # | Item | Origin, path | License | Mode | Destination | Changes (concrete) | Acceptance tests | Milestone / card |
|---|---|---|---|---|---|---|---|---|
| 21 | SHA-256 manifest | ARC `researchclaw/hitl/checksums.py` (119 lines) | MIT | copy + adapt | `research_harness/core/hashing.py` | Canonical JSON (sorted keys, no NaN), BOM strip, CRLF/CR → LF for text files, streaming; no other behaviour change | Hashing unit tests (M1-02 DoD), T24 | M1 / M1-02 |
| 19 | Stage contracts | ARC `researchclaw/pipeline/contracts.py` (`StageContract`, `CONTRACTS`), `stages.py` | MIT | adapt | `research_harness/state/contracts.py` | Keep the dataclass shape (inputs, outputs, DoD, error code, retries); replace the 23 ARC stages with A0–A16 / T0–T10 as data (`lifecycle/*_stages.yaml`); add `gate` | T10, T29a | M1 / M1-04 (shape), M1-11 (stages) |
| 20 | Atomic checkpoints, resume | ARC `researchclaw/pipeline/runner.py`: `_write_checkpoint`, `_write_heartbeat`, `read_checkpoint`, `resume_from_checkpoint` | MIT | adapt (functions only) | `research_harness/state/{snapshot,recovery}.py` | Temp + fsync + rename pattern kept; checkpoint replaced by snapshot manifest (02 §5.2); heartbeat → lock holder metadata; resume → recovery table (02 §5.5); no silent rerun of side effects | T10 (fault injection) | M1 / M1-04 |
| 32 | Source dedup | OpenDraft `engine/utils/deduplicate_citations.py` (384 lines) | MIT | adapt | `research_harness/materials/dedup.py` (M1), reused by `sources/` (M2) | DOI / URL / title / author+year matching kept; **link** duplicates (`duplicate_of`, `preprint_of`, `published_version_of`) instead of merging; Cyrillic-aware title normalization (NFC, case-fold, transliteration-insensitive) | T38 (M1), T43 (M2) | M1 / M1-09; M2 / M2-01 |
| 31 | DOI / URL existence | OpenDraft `engine/utils/citation_validator.py` (486 lines) | MIT | adapt | `research_harness/sources/existence.py` | Crossref lookup and URL status only; timeout / 5xx → `lookup_failed`, never `not_found`; 404 from Crossref → `not_found`; no paid APIs; results feed `metadata_status` only, never `support` | T02, D5 | M2 / M2-01 |
| 17 | Retraction check | paper-qa `src/paperqa/clients/retractions.py` (`RetractionDataPostProcessor`, 92 lines) | Apache-2.0 | adapt | `research_harness/sources/retractions.py` | Drop the paper-qa client framework; plain function over Crossref Labs / Retraction Watch data; statuses `unknown` / `no_notice_found` / `notice_found` with `checked_at` and data source; **terms of use of the Retraction Watch data checked before adoption** [?]; Apache-2.0 modification notice | New `test_retraction_status` (three states + network failure → `unknown`); T02 | M2 / M2-01 |
| 30 | Claim–citation pair structures | OpenDraft `engine/utils/citation_claim_verifier.py` (`ClaimCitationPair`, `CitationClaimVerdict`, `CitationClaimVerifier`) | MIT | adapt **structures only** | `research_harness/claims/pairs.py` | Keep the split "source exists" vs "content assessment" and the UNCERTAIN idea (→ `unverifiable` / `insufficient`); **remove** the 25-pair cap and the 25k + 25k character truncation; coverage reports the full denominator; the LLM judge is not taken (#34 replaces it) | T08, N3 | M2 / M2-06 |
| 15 | Evidence-first prompts | paper-qa `src/paperqa/prompts.py`: `summary_prompt`, `summary_json_prompt`, `qa_prompt`, `answer_iteration_prompt_template`, `citation_prompt` | Apache-2.0 | adapt (text) | `harness/prompts/researcher.md` (extraction), `harness/prompts/unit_critic.md` (support check) | Output must be our excerpt / verdict schema; cite keys = our `bib_key`; refusal on insufficient evidence kept; locator with two page numberings; Apache-2.0 modification notice in front matter | T06, T30, T59 | M2 / M2-13 (researcher), M2-11 (unit critic) |
| 2 | Citation verification procedure | OPM `skills/verification-engine/SKILL.md` (385 lines) | MIT | adapt | `harness/skills/citation-support/SKILL.md`, `harness/prompts/unit_critic.md` | **Rubric mapping:** VERIFIED → `supported` only if an excerpt with locator states the claim; **PLAUSIBLE → `partial` or `insufficient`, never `supported`** (doc 12 §5.2, N1); MISMATCH → `contradicted`; UNVERIFIABLE → `unverifiable`, or `insufficient` when only the abstract was read (D2); NOT FOUND → `not_found` only after `metadata_status = not_found` (timeout → `lookup_failed` → `unverifiable`). Tier A/B/C access → `access_level`. Prioritization Tier 1–3 kept as ordering, never as sampling: unchecked claims are listed as `unchecked` (N3). Lookups go through `rh source lookup`, not ad-hoc API calls | T06, N1, T08 | M2 / M2-11 (critic), checks in M2-06 |
| 34 | Critic prompts | OpenDraft `engine/prompts/04_validate/skeptic.md`, `referee.md`, `factcheck_extract.md`, `factcheck_judge.md` | MIT | adapt | `harness/prompts/{unit_critic,chapter_critic}.md` | Judge rewritten to our support verdicts and finding schema (02 §9.4); no scores without findings; Gemini / paid-API references removed | T06, T13, N1 | M2 / M2-11 (unit level), M3 (`04-modules/review.md`) |
| 6 | Simulated peer review | OPM `skills/peer-review-engine/SKILL.md` (506 lines), `commands/review-paper.md` | MIT | adapt | `harness/skills/peer-review/SKILL.md` (merged with K-Dense `peer-review`) | Advisory only; output = findings with location and evidence; no accept / reject verdict for the paper; no approval rights | T13 | M2 / M2-11 (unit level); M3 (chapter, integration) |
| 4 | Literature search procedure | OPM `skills/literature-engine/SKILL.md` (346 lines) | MIT | adapt | `harness/skills/literature-search/SKILL.md`, `harness/prompts/researcher.md` | **Replace every reference to `scripts/academic_search.py`** (lines 6, 25, 51, 253 [V]) with `rh search plan` / `rh search run --adapter …` / `rh search log`; do not adopt the MCP `academic-search-mcp` (ADR-016 p.3); add "not checked ≠ nothing found", Ukrainian resources (НБУВ, OJS journals) and manual-export flow for Scopus / WoS / Scholar (`06-research-agent.md` §3.1) | T59, T20, N5 | M2 / M2-03 (commands), M2-13 (skill) |
| 1 | Orchestration procedure | OPM `agents/paper-machine.md` (793 lines) | MIT | adapt | `harness/prompts/orchestrator.md`, `AGENTS.md` §2 | Replace PHASE 0–8 and RS1–RS8 with the `rh status` loop (05 §4) and stages A0–A16; remove the references to `scripts/academic_search.py` (lines 201, 222, 242 [V]); the orchestrator never drafts large-document text (ADR-010 rev.2); keep the orchestration-log idea as `lablog/` | T44, T35, N5 | M2 / M2-13 |
| 8 | Drafting procedure | OPM `skills/writing-engine/SKILL.md` (494 lines), `commands/draft-section.md` | MIT | adapt | `harness/prompts/writer.md`, `harness/skills/unit-drafting/SKILL.md` | Input = unit brief + context pack; author contribution points as placeholders (FR-45); claims ledger entries per paragraph; voice and language rules (02 §1.6, FR-51); no fixed paragraph templates that override the author's style (FR-19) | T49, T07, T57 | M2 / M2-10, M2-13 |
| 9 | Method, theory, positioning | OPM `skills/method-engine/SKILL.md` (797 lines), `theory-engine` (178), `positioning-engine` (286) | MIT | adapt | `harness/prompts/analyst.md`, `harness/skills/{protocol-literature,positioning}/SKILL.md` | method-engine **shortened** to literature / conceptual protocols for M2 (empirical parts move to M3 / M6); positioning output = gap statements as claims with evidence refs (A3); theory-engine → premise / definition evidence type (ADR-013) | T03, T30 | M2 / M2-05, M2-13 |
| 7 | Idea assessment (A1) | OPM `skills/idea-engine/SKILL.md` (213), `agents/idea-critic.md` (148), `research-strategist.md` (149), `brainstormer.md` (123), commands `evaluate-idea`, `scooping-check`, `triage-project` | MIT (+ research-companion MIT, if its text is present [?]) | adapt | `harness/skills/idea-assessment/SKILL.md`, `harness/prompts/analyst.md` | Output = A1 decision record (pursue / refine / kill) for the **author** to decide; scooping check via `rh search`; before adoption compare the agent texts with research-companion and add its notice if text was taken | New `test_a1_decision_record` (record exists, decision is human); T35 | M2 / M2-13 |
| 3 | Paper ↔ results audit | OPM `skills/audit-engine/SKILL.md` (415 lines) | MIT | copy + extend | `harness/skills/results-audit/SKILL.md` | Link to result rows and run provenance (FR-05, FR-06); CONFIRMED / PARTIAL / MISSING / MISMATCH / NOT_AUDITABLE mapped to findings | T05, T04 | M3 (`04-modules/analysis-sandbox.md`) |
| 5 | Respond to reviewers | OPM `skills/review-engine/SKILL.md` (600 lines), `commands/respond-reviewers.md` | MIT | adapt | `harness/skills/respond-reviewers/SKILL.md` | Table comment → action → location → evidence → response; edits only in declared places (FR-21); disagreement with evidence; the author decides each response | T21, T44 | M3 (`04-modules/review.md`) |
| 11 | CRediT, human / AI split | OPM `skills/coauthor-engine/SKILL.md` (179 lines) | MIT | adapt | `harness/skills/ai-use-and-credit/SKILL.md` | AI-use record built from paragraph provenance (FR-53) and model-call log; never phrased to minimise AI involvement (N4) | T34, T58 | M3 (`04-modules/integrity.md`) |
| 22 | Budget thresholds | ARC `researchclaw/hitl/cost_guard.py` (132 lines) | MIT | adapt | `research_harness/budget/guard.py` | Thresholds 50 / 80 / 100% kept; **add state `unknown`** when telemetry is missing (never treated as 0); check before every model call, search call, compute; stop with partial artifacts at 100%; paid calls disabled (ADR-017) | T61 (M2), T12 (M3) | M2 / M2-09 |
| 23 | Version diff | ARC `researchclaw/hitl/diff_view.py` (151 lines) | MIT | adapt | `research_harness/text/diff.py` | Unit-level diffs for agent edits shown before applying (02 §5.6); paragraph IDs preserved; Cyrillic-safe | T07 (M2), T21 (M3) | M2 / M2-10 |
| 14 | K-Dense scientific skills (8) | see §4 | MIT | adapt / copy selectively | see §4 | see §4 | see §4 | M2–M3 |

### 3.2. Ideas only (no text copied)

| # | Item | Origin, path | Why idea only | Where the idea is used |
|---|---|---|---|---|
| 13 | Figures via PaperBanana | OPM `skills/figure-engine/SKILL.md`, `scripts/paperbanana_direct.py` | Generates images with Gemini; result figures must come from data (FR-18) | Schematic figures, if ever: LATER |
| 16 | Agent tools / environment state | paper-qa `src/paperqa/agents/tools.py` | Own LLM runtime (fhaviary, lmi, litellm) — conflicts with ADR-001 | Context pack / task state design (05 §2–3) |
| 24 | Condition names, training config check | ARC `researchclaw/pipeline/paper_verifier.py` | Depends on rejected `verified_registry.py` | Our tuple validators (M3) |
| 27 | Stage prompts, budget scaling | ARC `prompts.default.yaml` | Cutting seeds to save time is a protocol deviation | — |
| 28 | Phase generator, preconditions | OpenDraft `engine/draft_generator.py`, `engine/phases/*.py` | Bound to Gemini and paid APIs | Stage contracts (M1-04) |
| 29 | Checkpoint per phase | OpenDraft `engine/utils/checkpoint.py` | Duplicates #20; one pattern only | — |
| 33 | Citation DB schema | OpenDraft `engine/utils/citation_database.py` | Own Source / Excerpt schemas (02 §12) | — |
| 35 | Author voice | OpenDraft `engine/prompts/05_refine/voice.md` | Style profile is author-controlled and built from his corpus (FR-19) | Style profile (M3) |
| 37 | Experiment journal, tree search | AI-Scientist-v2 `ai_scientist/treesearch/journal.py`, `agent_manager.py`, `parallel_agent.py` | License §3.2.e.i requires a disclosure in every manuscript; §3.3 passes restrictions on | Lab journal (M2-03) — own design |
| 38 | LLM / VLM review | AI-Scientist-v2 `ai_scientist/perform_llm_review.py`, `perform_vlm_review.py` | Same license | Figure review idea for FR-17 (M3) |

### 3.3. Rejected (never copied, checked by `rh-dev check`)

| # | Item | Origin, path | Reason |
|---|---|---|---|
| 25 | "Verified" numbers registry | ARC `researchclaw/pipeline/verified_registry.py` | Membership check with ×100 / ÷100 variants and 1% tolerance — no tuple (ADR-009, N2) |
| 26 | Numeric / factual claim check | ARC `researchclaw/hitl/claim_verifier.py` | Reproduced false positive (95 s ≈ 95% accuracy); word overlap ≠ entailment (ADR-009) |
| 36 | Anti-AI-detection styling | OpenDraft `engine/prompts/05_refine/entropy.md` | Aims to hide AI origin — integrity (addendum §3, N4, decision 2026-10-28) |
| 18 | Journal quality data | paper-qa `client_data/journal_quality.csv` | Unknown data origin; venue status via MJL / Scopus Sources (FR-37) |
| — | PyMuPDF reader | paper-qa `packages/paper-qa-pymupdf` | AGPL-3.0 |
| — | External agents | ARC `external/agents/*` | No license files |
| 10 | Screening / PRISMA | OPM `skills/screening-engine/SKILL.md`, `commands/screen-papers.md` | Not rejected for good: **LATER** with FR-15c |
| 12 | Submission, LaTeX, slides | OPM `submission-engine`, `latex-engine`, `presentation-engine` | **LATER**; may be reconsidered after MVP |

## 4. K-Dense scientific skills (registry #14)

All 8 chosen by the author on 2026-10-27 (`02-lifecycle.md` §14). Taken from upstream `K-Dense-AI/claude-scientific-skills @ 5f2bc0341354fd5590aef76a533ada1e1e5b4e62`, not from the OPM copies (doc 12 §7). Front matter, versions, section headings, bundled scripts and external dependencies were read on 2026-10-29 **[V]**; full bodies are read at adoption (§2 step 4).

Common to all eight: each has a section "Citing Scientific Agent Skills" asking the agent to add a citation of Kassis et al. (2026), arXiv:2609.00065, to any manuscript the skill materially contributed to, and to tell the user. **Change:** the agent never adds references to the manuscript on its own (H6, FR-45); the attribution goes into `THIRD_PARTY_NOTICES.md` and the AI-use record (FR-32), and whether to cite it in a paper is the author's decision.

| Skill (version, lines) | What it contains [V headings] | Stages / role | Mode | Keep | Cut or change | Destination | Card |
|---|---|---|---|---|---|---|---|
| `literature-review` (1.11, 229) | Search strategy; records vs reports vs studies; screening; synthesis; quality and reproducibility; PRISMA figures; verification scope | A2, T2 / researcher | adapt | Records-vs-studies distinction, documented search strings / dates / counts, synthesis and quality guidance, "ranked results cannot establish exhaustive coverage" | **Cut** `parallel-cli` (needs Parallel authentication), OpenRouter AI schematics (`OPENROUTER_API_KEY`), PDF generation via Pandoc / XeLaTeX; PRISMA flow → LATER (FR-15c); searches only through `rh search` | `harness/skills/literature-search/SKILL.md` (merged with OPM #4) | M2-13 |
| `citation-management` (2.3, 359) | Discovery (OpenAlex, PubMed, Google Scholar); metadata extraction; "Phase 2.5 metadata enrichment via web search (mandatory)"; BibTeX formatting; validation; scripts `search_openalex.py`, `doi_to_bibtex.py`, `validate_citations.py`, `search_google_scholar.py` | A2, A11 / researcher, unit_critic | adapt | Metadata extraction and validation steps; BibTeX formatting rules; pitfalls list | **Cut** Google Scholar via `scholarly` (scraping, ADR-016; Scholar stays manual / browser-assisted per `06-research-agent.md` §3.1a); **change** "web search enrichment" to enrichment only from OpenAlex / Crossref, with web-found metadata marked `unverified`; scripts are **not vendored** — our adapters (M2-01) implement lookups; PubMed optional | `harness/skills/citations/SKILL.md` | M2-13 (skill), M2-01 (adapter behaviour) |
| `scientific-critical-thinking` (1.5, 235) | Appraisal workflow; biases and confounders; evidence grading (GRADE, Cochrane RoB); critique and uncertainty guidance | A1, A3, A7, A11 / analyst, critics | adapt | Appraisal workflow, risk-of-bias at the right unit, "when uncertain" rules | **Cut** optional schematics via OpenRouter; medical-specific examples shortened for educational sciences | Shared section in `harness/prompts/{analyst,unit_critic,chapter_critic,integration_critic}.md` | M2-11 (critic), M2-13 (analyst) |
| `peer-review` (2.4, 317) | Safety boundary (confidentiality, authorization); human accountability; intake gate; claim → evidence map; methods / statistics / reproducibility / ethics / figures / citations review; actionable comments; local deterministic CLIs (stdlib, no network) | A11, A14 / critics | adapt | Claim–evidence mapping, review structure, actionable comment format, "never announce a decision that belongs to an editor", confidentiality rules (apply to reviewer comments received in A14) | Authorization gate simplified: the author's own manuscript is authorized by intake; bundled CLIs **not vendored** (our checks are in `rh`) — used as reference for finding fields | `harness/skills/peer-review/SKILL.md` (merged with OPM #6) | M2-11; M3 |
| `scientific-writing` (2.3, 381) | No fabrication; evidence binding; scientific fidelity; evidence outline; "draft without adding facts"; methods ↔ results reconciliation; citation and claim verification; authorship and disclosure; reporting guidance | A8, A9 / writer | adapt | No-fabrication and evidence-binding rules, evidence outline → our section brief, "draft without adding facts", disclosure section → AI-use record | Bind to our claim ledger, briefs, author contribution placeholders, language rule (02 §1.6); submission formatting → LATER; reporting guidelines → rule packs | `harness/prompts/writer.md`, `harness/skills/unit-drafting/SKILL.md` (merged with OPM #8) | M2-13 |
| `hypothesis-generation` (2.4, 290) | Scope and safety gate; frozen observation; question framing; dated evidence boundary; rival hypotheses; claim type and estimand; discriminating predictions; measurement; design ↔ analysis; anti-HARKing; replication; human accountability; local CLIs | A1, A4 / analyst | adapt | Rivals before tests; dated evidence boundary; anti-HARKing and deviation logging (matches G2); human accountability | Split from OPM idea-engine (#7): idea-engine = pursue / refine / kill decision support; hypothesis-generation = questions, rivals, predictions for the protocol. Empirical parts used from M3; conceptual premises in M2 | `harness/skills/protocol-literature/SKILL.md` (section), `harness/prompts/analyst.md` | M2-13 (conceptual; used by M2-05 protocol), M3 |
| `statistical-analysis` (2.0, 453) | Test selection; assumption checks; effect sizes and CIs; power analysis; Bayesian alternatives; APA reporting; script `assumption_checks.py` | A6–A7 / analyst (sandbox) | adapt | Test selection guide, assumption checks, effect sizes with CI, reporting templates | Runs only inside the analysis sandbox (FR-54 p.4) with our lockfile; every reported number goes through result rows and tuple validators (ADR-009); reporting style from rule packs, not fixed APA; check its package list (pingouin, PyMC / ArviZ for Bayesian) against the sandbox stack before adoption [?] | `harness/skills/statistical-analysis/SKILL.md` | M3 (`04-modules/analysis-sandbox.md`) |
| `scientific-visualization` (1.4, 307) | Non-negotiable guardrails; honest encoding; accessibility; scoped styles; explicit export with provenance; inspection; bundled CLIs (metadata, palette audit, export plan) | figures (FR-17, FR-18) / analyst | adapt | Guardrails, accessibility, provenance of transformations, export checklist | Figures only from result rows by code (FR-18); **cut** Plotly static export via Kaleido (needs Chrome); publisher rules → rule packs; CLIs used as reference, not vendored | `harness/skills/figures/SKILL.md` | M3 (`04-modules/analysis-sandbox.md`) |

## 5. Adoption order by card

| Card | Records |
|---|---|
| M1-02 | #21 |
| M1-04 | #19, #20 |
| M1-09 | #32 |
| M2-01 | #31, #17, #32 (extended), K-Dense `citation-management` behaviour for adapters |
| M2-03 | #4 (command side) |
| M2-05 | #9 (protocol part) |
| M2-06 | #30 |
| M2-09 | #22 |
| M2-10 | #23, #8 (procedure) |
| M2-11 | #2, #6, #34, #15 (critic part); K-Dense `peer-review`, `scientific-critical-thinking` |
| M2-13 | #1, #4, #7, #8, #9, #15 (researcher part); K-Dense `literature-review`, `citation-management`, `scientific-writing`, `hypothesis-generation` (conceptual), `scientific-critical-thinking` (analyst) |
| M3 | #3, #5, #11, #34 (chapter / integration), #6 (chapter / integration); K-Dense `statistical-analysis`, `scientific-visualization`, `hypothesis-generation` (empirical) |

## 6. Open items for adoption time

| # | Item | Blocks |
|---|---|---|
| 1 | Terms of use of the Retraction Watch data served via Crossref Labs | #17 adoption (M2-01) |
| 2 | Whether OPM idea agents contain text from andrehuang/research-companion; resolve its SHA if yes | #7 adoption (M2-13) |
| 3 | Licenses of transitive dependencies of anything vendored (doc 12 §4: not audited) | Any `copy` of code with imports |
| 4 | `statistical-analysis` package list vs sandbox stack | M3 |
