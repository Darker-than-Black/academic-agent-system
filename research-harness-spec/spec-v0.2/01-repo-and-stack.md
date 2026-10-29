# 01 — Repository Layout and Stack

Sources: ADR-001 rev.2, ADR-002 (`05-architecture.md`), ADR-014 rev.2, ADR-019, NFR-02, NFR-06, NFR-07, NFR-11, NFR-14, `05-eval-base.md` §2.

## 1. Two trees: harness and workspace

ADR-014 rev.2: for the author, one private repo holds both the harness and his workspace. For other users the workspace is a separate directory created by `rh init-workspace`. The workspace structure is identical in both cases, and **no code may assume the workspace is inside the harness repo.** The workspace path is always resolved from `--workspace`, then `RH_WORKSPACE`, then the nearest parent directory containing `.rh-workspace.json`.

## 2. Harness repository

```
research-harness/                      git root (author's private repo)
├── AGENTS.md                          shared agent rules (both hosts); see M1-14
├── CLAUDE.md                          one line importing AGENTS.md (syntax per Claude Code docs)
├── README.md
├── LICENSE                            Apache-2.0 (decision 2026-10-29)
├── NOTICE                             Apache-2.0 NOTICE: harness copyright + pointer to THIRD_PARTY_NOTICES.md
├── PROJECTS_NOTICE.md                 states that the harness license does not cover Projects/
├── THIRD_PARTY_NOTICES.md             notices for every adopted file
├── .gitignore                         see §5
├── .claude/settings.json              deny rules for **/holdout/** and private paths (M1-14)
├── harness/
│   ├── pyproject.toml                 package research-harness; entry points rh, rh-dev
│   ├── uv.lock
│   ├── src/research_harness/
│   │   ├── core/                      ids, hashing, time, paths, envelope, errors   (M1)
│   │   ├── schemas/                   JSON Schema files shipped as package data      (M1)
│   │   ├── state/                     lock, staging, snapshots, events, recovery,
│   │   │                              idempotency, freshness/invalidation           (M1)
│   │   ├── workspace/                 workspace, _author/, object folders, rename    (M1)
│   │   ├── structure/                 structure.yaml, units, renumber                (M1)
│   │   ├── rules/                     rule-pack loader, resolver, freshness          (M1)
│   │   ├── intake/                    questionnaire engine, G0 summary               (M1)
│   │   ├── materials/                 manifest, BibTeX/RIS/DOI-list import           (M1)
│   │   ├── gates/                     approval requests and records                  (M1)
│   │   ├── lifecycle/                 stage model A0–A16 / T0–T10, routing, status   (M1)
│   │   ├── models/                    model-tier config, call log                    (M1)
│   │   ├── migrate/                   schema migrations                              (M1)
│   │   ├── evals/                     eval runner (not the cases)                    (M1)
│   │   ├── cli/                       argument parsing and command handlers          (M1)
│   │   ├── i18n/                      message catalogs uk.yaml, en.yaml; lookup      (M1)
│   │   └── …                          M2+: sources, library, lab, claims, summaries,
│   │                                  context, export_docx, review, overlap, budget,
│   │                                  analysis, thesis — created by their cards only
│   ├── src/research_harness_dev/      rh-dev: repo checks, fixture generators       (M1)
│   ├── rulepacks/<pack-id>/           rule packs as data (§02 data model §8)        (M1+)
│   ├── intake/questions.yaml          intake questionnaire as data (texts uk + en)   (M1)
│   ├── gates/G0.yaml … GE.yaml        gate definitions and briefing texts (uk + en)  (M1)
│   ├── prompts/<role>.md, _common.md  role prompts, versioned (05-agents §5)         (M2)
│   ├── skills/                        adapted procedures (OPM, K-Dense) (06-reuse)   (M2)
│   ├── config/
│   │   ├── roles.yaml                 role → model_tier                              (M1)
│   │   ├── model-tiers.yaml           host → tier → model ID                         (M1)
│   │   ├── source-policy.yaml         M2; secrets only as env-var names
│   │   ├── context-budgets.yaml       M2; pack budgets per role
│   │   ├── prompts.yaml               M2; prompt language per role (05-agents §8)
│   │   └── labels.yaml                M1; unit-name labels per language
│   ├── host/
│   │   ├── claude-code/               skills, subagent definitions, commands         (M1 min, M2+)
│   │   └── codex/                     Codex adapter                                  (M3)
│   ├── third_party/
│   │   ├── manifest.json              adoption records (schema in 02 §13)
│   │   └── <origin-repo>/…            adopted files with their original headers
│   ├── evals/
│   │   ├── cases/                     YAML cases (05-eval-base §5.2)
│   │   ├── fixtures/                  generators + generated synthetic fixtures (F5, F7, F8)
│   │   ├── results/                   aggregated results, decisions.md, holdout-log.jsonl
│   │   └── holdout.lock.json          IDs and hashes only (author creates, before M2 gate)
│   └── tests/
│       ├── unit/  integration/  fault/
│       └── conftest.py
└── Projects/                          author's workspace (structure in §4)
```

Rules:
- Package directories are created by the card that needs them. Do not create empty modules "for later".
- `src/research_harness_dev/` may import `research_harness`; never the reverse.
- Host adapters under `harness/host/` call `rh`; `research_harness` never imports them (H5).

## 3. Stack

ADR-002 is binding: Python CLI `rh`, Markdown + JSON/JSONL/YAML on disk, JSON Schema Draft 2020-12, code-level cross-reference validators, minimal dependencies. The implementer fixes exact versions after checking compatibility and records them in the lockfile.

| Concern | Choice | License (verify at adoption) | Milestone | Status |
|---|---|---|---|---|
| Python | ≥ 3.12, managed by `uv`; version pinned in `pyproject.toml` and `.python-version` | PSF | M1 | [P] |
| Packaging / env | `uv` (lockfile committed) | MIT / Apache-2.0 | M1 | [P]; `uv` is also the sandbox tool (`06-research-agent.md` §3.4) |
| CLI parsing | `argparse` (stdlib) | PSF | M1 | ADR-002 |
| Schemas | `jsonschema` with Draft 2020-12 validator | MIT | M1 | ADR-002 |
| YAML | `PyYAML` safe loader only | MIT | M1 | [P] |
| BibTeX | `bibtexparser` **v2** | MIT for v2 [?] — v1 was dual LGPL/BSD; confirm the license of the exact version | M1 | [P] |
| RIS | `rispy` | MIT [?] | M1 | [P] |
| User-facing messages | Own YAML message catalogs `i18n/uk.yaml`, `i18n/en.yaml` with `str.format` placeholders; no gettext toolchain | — | M1 | Decision 2026-10-29; 02 §1.6 |
| Unicode / transliteration | stdlib `unicodedata` (NFC); transliteration table for Ukrainian per the official KMU 2010 scheme implemented in-house as data | — | M1 (NFC), M2 (translit) | [P] |
| Tests | `pytest`; property tests with `hypothesis` optional | MIT / MPL-2.0 | M1 | [P] |
| Lint / format | `ruff` | MIT | M1 | [P] |
| Full-text index | SQLite FTS5 (stdlib `sqlite3`) | Public domain | M2 | [P]; tantivy rejected for M2 to avoid a native dependency |
| PDF text by page | `pypdf` first; `pdfminer.six` as fallback for layout | BSD-3 / MIT [?] | M2 | [P] |
| DOCX export | `pandoc` as an external binary called by subprocess, with a `reference.docx` per rule pack; bookmarks via `python-docx` post-processing | GPL binary not linked or vendored; `python-docx` MIT | M2 | [P] |
| DOCX import with tracked changes and comments | `python-docx` + direct OOXML parsing of `w:ins`, `w:del`, `w:comment` | MIT | M3 | [P] |
| Analysis sandbox | separate `uv` project per object with its own lockfile; pandas, numpy, scipy, statsmodels, matplotlib | BSD / PSF-like | M3 | `06-research-agent.md` §3.4 |

**Forbidden dependencies:** any LLM SDK in `research_harness` (NFR-07); PyMuPDF / `fitz` and `paper-qa-pymupdf` (AGPL-3.0); `paper-qa` runtime (own LLM runtime, registry #16); any package that needs a paid API key to import. A dependency check in `rh-dev check` enforces the first two (M1-02).

## 4. Workspace layout

```
Projects/                                   workspace root
├── .rh-workspace.json                      workspace ID, schema_version, ID counters per year
├── _author/                                author level (ADR-011 rev.2 p.3, FR-44)
│   ├── profile.yaml                        name, ORCID, affiliation, languages, default autonomy, voice
│   ├── publications.bib                    own publications
│   ├── style/<lang>/profile.yaml           style profiles (FR-19), M3
│   ├── errors-profile.yaml                 chosen typical-error categories (FR-51), M3
│   ├── corpus/                             own texts for overlap and style (FR-30, ADR-018)
│   └── versions.jsonl                      immutable version log of every file above
├── <Title>__A-2026-001/                    one article (FR-42)
└── <Title>__T-2026-001/                    one thesis
```

Object folder (article or thesis; same model, ADR-019 p.2):

```
<Title>__A-2026-001/
├── object.json             identity, kind, mode, stage states, pinned author-profile version
├── brief.md                human-readable brief (A0 output)
├── intake/                 answers.json, summary.md
├── materials/manifest.json materials manifest (FR-36)
├── profiles/resolved-stack.json
├── structure.yaml          single source of order and hierarchy (FR-46)
├── map.md  glossary.md     M2
├── manuscript/
│   ├── 01 Вступ/text.md  brief.md  summary.md  claims.json
│   ├── 02 Розділ 1. Назва/
│   │   ├── 1.1 Назва/…
│   │   └── 1.4 Висновки до розділу 1/…
│   └── …
├── protocol/ sources/ evidence/ lab/ lablog/ claims/ context/   M2
├── results/ runs/ analysis/                                M3 (analysis-sandbox.md)
├── approvals/                                             M1
├── reviews/ findings/                                     M2 (v0), M3
├── integrity/ venue/ ethics/ records/ locks.json          M3 (integrity.md, lifecycle-records.md)
├── thesis/                                                M4, thesis objects only
├── assets/ history/ export/                               M2+
├── work/                                                  scratch of delegated agents (gitignored)
└── .rh/                    machine state (02 data model §5); never edited by hand
    ├── CURRENT  lock  events.jsonl  model-calls.jsonl
    ├── snapshots/<snapshot-id>.json
    ├── objects/<sha256>    content-addressed blobs of managed files
    ├── staging/  quarantine/
```

Rules:
- Paths stored anywhere are relative to the object folder (or to the workspace root for `_author/`), POSIX separators, NFC-normalized. Absolute paths and `..` are rejected for managed artifacts (NFR-02).
- Folder and file names are NFC on creation; lookups compare NFC (macOS file systems may return NFD) (NFR-14).
- Forbidden name characters `: ? « » / \ * | < > "` are removed; leading/trailing spaces and trailing dots are stripped; the title part is cut to 60 characters at a word boundary where possible; the ID suffix is never cut (FR-42, ADR-014 p.3).

## 5. What never enters git

Enforced by `.gitignore` (M1-01) and by `rh-dev check` (M1-01 baseline; full PR check with T41 in M3):

| Pattern | Why |
|---|---|
| `**/holdout/**`, files whose hash is in `harness/evals/holdout.lock.json` | H1 |
| `Projects/**/sources/inbox/**`, `Projects/**/sources/fulltext/**`, `Projects/**/sources/pagetext/**` | Foreign full texts (NFR-11) |
| `Projects/**/materials/private/**`, any file listed with `private: true` in a materials manifest | NFR-11 |
| `.env`, `*.local.yaml`, `**/secrets/**`, `source-policy.local.yaml` | H8 |
| `Projects/**/.rh/staging/**`, `Projects/**/.rh/quarantine/**`, `Projects/**/.rh/lock`, `Projects/**/work/**` | Transient state |
| `Projects/**/.rh/library.sqlite` | Rebuildable full-text index of foreign texts |
| `Projects/**/analysis/data/**` when the dataset has `storage: no_copy` | Dataset terms (FR-57) |

`.rh/objects/`, `.rh/snapshots/`, `.rh/events.jsonl` **are committed** so that snapshots are portable and archived versions survive (NFR-02, NFR-10). Blobs are deduplicated by hash; blobs of files that are gitignored are never written to `.rh/objects/` — the snapshot keeps only their hash and locator (decision 2026-10-29, §7 Q2).

## 6. Host configuration

| Host | Files | Milestone |
|---|---|---|
| Claude Code | `AGENTS.md`, `CLAUDE.md`, `.claude/settings.json` (deny rules), `harness/host/claude-code/` (skills, subagents, commands) | M1 minimal (M1-14), M2 full |
| Codex | `AGENTS.md` (shared), `harness/host/codex/` and Codex config with equivalent deny rules | M3 |

Deny rules must cover reading `**/holdout/**` and the private patterns of §5. The exact settings syntax is verified against current host docs (H12).

## 7. Questions resolved by the author

| # | Question | Decision (2026-10-29) | Consequence |
|---|---|---|---|
| Q1 | Harness license | **Apache-2.0** | `LICENSE` with the full Apache-2.0 text and a `NOTICE` file (M1-01). Adopted MIT and Apache-2.0 files keep their own licenses and notices in `THIRD_PARTY_NOTICES.md`; `PROJECTS_NOTICE.md` states that Apache-2.0 does not cover `Projects/` |
| Q2 | Commit snapshot blobs (`.rh/objects/`) | **Commit** | §5 as written: blobs of text and JSON are committed; blobs of gitignored files are never written |

## 8. Human-readable repository docs

Root `README.md`, `harness/host/*/README.md` and `MIGRATIONS.md` are read by the author, so they are written in Ukrainian (02 §1.6). An English version (`README.en.md`) is added if the harness is published for other users. `AGENTS.md` and this spec are agent instructions and stay in English (02 §1.6).
