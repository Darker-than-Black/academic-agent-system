# 02 — Data Model, State and Invariants

Sources: ADR-002, ADR-011 rev.2, ADR-012, ADR-013, ADR-014 rev.2, ADR-015, ADR-019, ADR-020; FR-01, 07, 10, 11, 26–29, 33–36, 41–48, 53, 55; NFR-01, 02, 10, 12, 14, 16; v0.1 `06-contracts.md` and `schemas/claim.schema.json` (superseded but kept compatible where noted).

Every entity below gets a JSON Schema (Draft 2020-12) in `research_harness/schemas/`. The "M" column says when the schema must exist (**def**) and when behaviour around it must work (**impl**). M1 defines the contracts of later entities so that the state and invalidation engine is generic from day one (ADR-007 rev.3 consequence: Run and ResultRow schemas land in M1).

## 1. Conventions

### 1.1. Record base

Every stored record (JSON object or JSONL line) has:

| Field | Type | Rule |
|---|---|---|
| `schema_version` | string | `"0.2"` for this spec; bumped only by a migration (§11) |
| `id` | string | Stable; never changes on rename or edit (§1.2) |
| `created_at` | string | UTC, RFC 3339 with `Z`, second precision or finer |
| `producer` | object | `{kind, name, version, role?, model_id?, model_tier?}`; `kind` ∈ `human` / `tool` / `model` / `unattributed` |
| `inputs` | array | `[{ref, sha256}]` — artifacts this record was derived from (§1.4) |

`unattributed` is used when `rh` detects a change it cannot attribute (§5.6). Downstream logic treats it as `model` until the author confirms otherwise.

### 1.2. Identifiers

| Entity | Format | Scope / allocator |
|---|---|---|
| Workspace | `W-<ULID>` | `.rh-workspace.json` |
| Article / Thesis | `A-YYYY-NNN` / `T-YYYY-NNN` (`NNN` widens to 4 digits after 999) | Per-year counters in `.rh-workspace.json` |
| Unit | `U-` + 8 Crockford base32 chars, random | Unique within the object; never reused |
| Material | `M-NNNN` | Object counter |
| Source | `S-NNNN` | Object counter |
| Excerpt | `E-NNNNN` | Object counter |
| Claim | `C-NNNN` (v0.1 pattern `^C-[0-9]+$` stays valid) | Object counter |
| Premise / Definition | `P-NNNN` / `DEF-NNN` | Object counter |
| Finding | `F-NNNNN` | Object counter |
| Approval request / Approval | `AR-NNNN` / `AP-NNNN` | Object counter |
| Dataset / Run / Result row | `D-NNN` / `R-NNNN` / `RR-NNNN-NNNN` (run + row) | Object counter |
| Paragraph (M2) | `PG-` + 6 Crockford base32 chars | Unique within the object |
| Submission / Publication record | `SUB-NN` / `PUB-NN` | Object counter (M3) |
| Reviewer comment (external) | `RC-NN` | Object counter (M3) |
| Asset | `AS-NNN` | Object counter (M3) |
| Thesis task / novelty item | `TK-N` / `NV-N` | Thesis object counter (M4) |
| Handoff | `H-` + ULID | Generated (M2, `05-agents.md` §2) |
| Operation / Snapshot / Event / Model call | `op-` / `snap-` / `ev-` / `mc-` + ULID | Generated |
| Rule | Pack-defined, e.g. `UA-PHD-SELFPLAG-01` | Unique within the pack |

Object counters live in `object.json` → `counters` and are only incremented inside a committed operation. ULIDs are generated in-house (stdlib, monotonic within a process).

### 1.3. Hashing

- Algorithm: SHA-256, lowercase hex, 64 chars.
- JSON records: hash of canonical JSON — `json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))` encoded as UTF-8. `NaN` and `Infinity` are rejected.
- Text files (`.md`, `.yaml`, `.yml`, `.bib`, `.ris`, `.txt`, `.csv`, `.json` when hashed as a file): strip a UTF-8 BOM, convert CRLF and CR to LF, hash the bytes. Content is **not** Unicode-normalized (that would alter the author's text).
- Binary files: raw bytes.
- Reuse: AutoResearchClaw `researchclaw/hitl/checksums.py` (registry #21) is the starting point; adoption record required (M1-02).

### 1.4. Artifact references

A reference names an artifact independently of its path, so renames do not break links (FR-42, FR-46):

```
<kind>:<id>[/<part>][@<version>]
```

| Example | Meaning |
|---|---|
| `unit:U-7K2M9QXA/text` | `text.md` of a unit (also `/brief`, `/summary`, `/claims`) |
| `source:S-0012` | Source record |
| `excerpt:E-00031` | Excerpt record |
| `rulepack:ua-mon-phd@2026-10-27` | Rule pack version |
| `author:profile@v3` | Version 3 of `_author/profile.yaml` |
| `object:A-2026-001/structure` | `structure.yaml` (also `/object`, `/intake`, `/materials`, `/stack`) |
| `file:materials/inbox/notes.txt` | Unmanaged file, by relative path (last resort) |

`inputs` and `dependencies` always pair a ref with the `sha256` observed when the record was produced.

### 1.5. Paths and text

- Stored paths: relative to the object folder (or workspace root for `_author/`), POSIX `/`, NFC. `..` segments and absolute paths are rejected (NFR-02).
- Names created by `rh` are NFC. Comparisons normalize both sides to NFC (NFR-14).
- Times: UTC everywhere in records; the CLI may display local time.

### 1.6. Languages (decision 2026-10-29)

The supported languages are Ukrainian (`uk`) and English (`en`). The rule: **anything a human reads is in that human's language; English is used only where no human reads it as prose, or where it is expected to improve result quality — and that expectation is tested.**

| Layer | Language | Reason |
|---|---|---|
| Manuscript: `text.md`, abstracts, dictation transcripts, summaries meant for the author | The object's language from intake: `languages.main`, `languages.abstracts` (one article in Ukrainian, another in English, a thesis in Ukrainian with an English abstract — all valid) | Articles and theses may be written in different languages |
| Author-facing output: CLI human messages, `status --format text`, envelope `message` and `next_actions[].why`, finding `reason` / `proposed_action`, intake questions shown to the author, `intake/summary.md`, gate briefings, repository READMEs, PR descriptions | `ui_language` from `_author/profile.yaml` (`uk` default); override per command with `--lang` or `RH_LANG` | The author reads them |
| Conversation with the agent | The language the author uses | — |
| Machine layer: code, identifiers, JSON / YAML keys, enum values, schema files, IDs, event and log keys, commit subjects | English | Not read as prose; changing it gives no quality gain and breaks tooling |
| Agent instructions: `AGENTS.md`, role prompts, skills, subagent definitions, this spec | English **[P, to be tested]** | Adopted skills and prompts (open-paper-machine, K-Dense, paper-qa) are in English, and translating them adds drift; models are expected to follow English instructions at least as reliably — an assumption, not measured for this harness. Every role prompt instructs the model to **write output in the object's manuscript language** and to address the author in his UI language. The M5 pilot runs one A/B task with English vs Ukrainian writer and critic prompts on a Ukrainian manuscript; if the Ukrainian prompts are equal or better on MS, MF and MY, prompts switch to Ukrainian |
| Rule statements | `statement` in English (machine-comparable) + `statement_original` in the source language; shown to the author in his UI language when a translation exists, else the original | Legal and journal texts must stay checkable against the source |

Implementation: user-facing strings live only in `research_harness/i18n/{uk,en}.yaml` and data files with `{uk, en}` text maps (intake questions, gate definitions); code refers to message keys. A missing translation falls back to the other language and is reported by `rh-dev check`.

## 2. Status vocabularies

Shared enums; each gets a `$defs` entry in `schemas/common.schema.json`.

| Enum | Values | Notes |
|---|---|---|
| `check_result` | `pass`, `fail`, `unknown`, `not_applicable` | `unknown` never counts as `pass` (H7) |
| `freshness` | `current`, `stale` | Always computed (§6), never stored as truth |
| `stage_state` | `pending`, `active`, `blocked`, `completed`, `failed`, `stale`, `waiting`, `not_applicable` | `waiting` = A16 (ADR-015 p.3); `blocked` requires `reason` and `next_action` |
| `severity` | `blocker`, `major`, `minor`, `info` | Only `blocker` blocks gates and verified export |
| `gate` | `G0`, `G1`, `G2`, `G3`, `GE` | ADR-011 p.5 |
| `decision` | `approved`, `rejected`, `approved_with_conditions` | |
| `actor_role` | `author`, `co_author`, `supervisor`, `ethics_committee`, `editorial_office`, `department`, `academic_council`, `defense_council` | FR-35 |
| `autonomy` | `step`, `gates`, `batch` | Default `gates` (ADR-015) |
| `operation_mode` | `create`, `revise`, `extend`, `respond_to_reviewers` | |
| `document_kind` | `article`, `thesis`, `conference_abstract`, `report` | MVP supports `article` and `thesis`; others resolve to `unknown` rule stacks |
| `study_kind` | `literature`, `conceptual`, `empirical_quantitative`, `empirical_qualitative`, `computational_ml`, `mixed`, `unknown` | `study_subtype` free string validated by the study-kind pack (e.g. `narrative`, `scoping`) |
| `metadata_status` | `unresolved`, `matched`, `ambiguous`, `not_found`, `lookup_failed` | Timeout → `lookup_failed`, never `not_found` |
| `access_level` | `metadata`, `abstract`, `fulltext`, `local_original` | |
| `support` | `unreviewed`, `supported`, `partial`, `insufficient`, `contradicted`, `not_found`, `unverifiable` | Extends v0.1 with `not_found`, `unverifiable` (05-eval-base §5.1). Coverage reports show `unreviewed` as **unchecked** |
| `retraction_status` | `unknown`, `no_notice_found`, `notice_found` | Always with `checked_at` |
| `resource_status` | `ok`, `unavailable`, `blocked`, `budget_exhausted`, `not_checked` | "Not checked" ≠ "nothing found" (FR-03) |
| `run_origin` / `run_status` | `executed`, `imported`, `simulated` / `planned`, `running`, `succeeded`, `failed`, `cancelled` | `simulated` never supports a claim (FR-05, FR-59) |
| `paragraph_origin` | `author`, `agent_edited_by_author`, `agent` | FR-53 |
| `rule_evidence_level` | `primary`, `secondary` | `[Н]` → `primary`; `[Н?]` → `secondary` |
| `rule_freshness` | `current`, `expired`, `not_yet_valid` | §8.4 |
| `pack_status` | `draft`, `verified`, `deprecated` | |
| `finding_status` | `open`, `accepted`, `rejected`, `fixed`, `unresolved` | Accept / reject require a human resolution (§9.3) |

## 3. Workspace and author level

### 3.1. `.rh-workspace.json` — M1 def+impl

| Field | Rule |
|---|---|
| `schema_version`, `id` (`W-…`), `created_at` | Base |
| `counters` | `{ "A": {"2026": 3}, "T": {"2026": 1} }` |
| `objects` | `[{id, kind, folder}]` — index for lookup by ID; rebuilt by `rh workspace reindex` if it disagrees with the folders on disk (folders win) |

### 3.2. `_author/` — M1 def+impl (style and error profiles M3)

| File | Content |
|---|---|
| `profile.yaml` | `name`, `name_latin`, `orcid`, `affiliations[]`, `languages[]` (languages he writes in), `ui_language` (`uk` / `en`, default `uk`; §1.6), `default_autonomy`, `voice` (`I` / `we` / `impersonal`), `contact_email?` |
| `publications.bib` | Own publications (BibTeX) |
| `corpus/` | Own texts for overlap (FR-30) and style (FR-19); files listed in `corpus/index.json` with `sha256`, `kind`, `published: bool`, `private: bool` |
| `versions.jsonl` | One line per change of any file above: `{id: "author:<file>@v<n>", file, version, sha256, created_at, producer}` |

Objects pin a version, never a live link (FR-44, T45): `object.json` → `author_pins: {"profile": {"ref": "author:profile@v3", "sha256": "…"}, …}`. A later author-profile change does not alter existing objects until the author explicitly re-pins (`rh author pin`).

## 4. Object

### 4.1. `object.json` — M1 def+impl

| Field | Rule |
|---|---|
| Base fields | `id` is `A-…` or `T-…` |
| `kind` | `article` / `thesis` |
| `title` | Human title (any language); folder name derives from it (01 §4) |
| `document_kind`, `operation_mode`, `study_kind`, `study_subtype?` | From intake; `unknown` allowed |
| `languages` | `{main: "uk", abstracts: ["uk", "en"]}` |
| `autonomy` | From intake Q10 or author default |
| `author_pins` | §3.2 |
| `stages` | Map stage ID → `{state, updated_at, reason?, next_action?, gate?}` for A0–A16 (article) or T0–T10 (thesis) |
| `counters` | Per-entity counters (§1.2) |
| `rename_history` | `[{from_title, to_title, at}]` |

`object.json` is a managed file inside every snapshot, so it must not contain the current snapshot ID (that lives in `.rh/CURRENT`).

### 4.2. Stage model — M1

Stage lists, gates and routing follow `02-lifecycle.md` §3 and §6 with v0.2.1 overrides:

| Stage | Gate on completion | Notes |
|---|---|---|
| A0 Intake | G0 | Mandatory before any other stage (FR-26) |
| A4 Protocol | G1 | |
| A5 Ethics | GE | `not_applicable` when `participants=false`; otherwise A6 is blocked without an external approval (FR-31) |
| A6 Evidence | G2 | Only on material deviation from protocol |
| A12 Venue | G3 | G3 binds to the snapshot hash; every new version needs a new G3 |
| A14 Reviews | G3 (new hash) | |
| A16 After publication | — | State `waiting`; never `completed` (ADR-015) |
| T0–T10 | External approvals with `actor_role` | Thesis gates are external approvals (§9.2) |

Entry routing (`rh start`, `rh continue`, later `revise`, `reviews`) follows `02-lifecycle.md` §5 and FR-41. M1 implements `start` and `continue`.

## 5. State: snapshots, operations, recovery — M1

### 5.1. Files in `.rh/`

| File | Content |
|---|---|
| `CURRENT` | One line: current snapshot ID |
| `snapshots/<snap>.json` | Snapshot manifest (§5.2) |
| `objects/<sha256>` | Content-addressed blob of a managed file |
| `events.jsonl` | Diagnostic event log; **snapshots are authoritative** (ADR-002) |
| `model-calls.jsonl` | Model call log (§10) |
| `lock` | Present while an operation runs (§5.4) |
| `staging/<op>/` | New file versions of an in-flight operation |
| `quarantine/` | Abandoned staging, corrupt log tails |

### 5.2. Snapshot manifest

| Field | Rule |
|---|---|
| Base fields | `id` = `snap-…`; `producer` = who caused the change |
| `parent` | Previous snapshot ID or `null` |
| `operation` | `{id, command, args_normalized, idempotency_key, request?}` — `request` = the author's instruction behind an agent edit (§5.6) |
| `files` | `[{path, ref?, sha256, size, stored: bool}]` — every managed file; `stored=false` for gitignored files (hash and locator only) |
| `manifest_sha256` | Hash of the manifest without this field; approvals bind to it |
| `tags` | e.g. `["submitted:2026-11-02"]`, `["published"]`; tagged snapshots are frozen for migrations (NFR-10) |

Managed files: everything in the object folder except `.rh/`, `export/` and gitignored patterns (01 §5). Gitignored files that are referenced (e.g. a PDF in `sources/inbox/`) are listed with `stored=false`.

### 5.3. Commit protocol

Every mutating command is one **operation**:

1. Run recovery (§5.5), then acquire the lock.
2. Compute the dirty set (§5.6). If it overlaps the operation's write set, stop with exit 3 and `next_action: rh checkpoint`.
3. Write new file versions into `staging/<op>/`; validate them (schemas, cross-references, invariants).
4. Write missing blobs to `objects/` (temp file → fsync → rename).
5. Write `snapshots/<snap>.json` (temp → fsync → rename). **This is the commit point.**
6. Materialize: move staged files into the working tree (temp → rename per file).
7. Update `CURRENT` (temp → fsync → rename).
8. Append the event (single line, fsync).
9. Delete staging, release the lock.

`idempotency_key = sha256(command + canonical(normalized args) + sha256 of inputs + config hash)`. If an operation with the same key already committed, return its result without new side effects (FR-11).

### 5.4. Lock

`.rh/lock` is created with `O_CREAT | O_EXCL` and holds `{operation_id, pid, hostname, command, started_at}`. A second writer gets exit 4 with the holder's details. A lock whose process is gone is **never** removed silently: commands report it, and `rh resume` performs explicit recovery (ADR-002).

### 5.5. Recovery

Run at the start of every command (read-only commands report, mutating commands repair):

| Situation | Action |
|---|---|
| Staging exists, no snapshot for it | Move staging to `quarantine/`; working tree untouched; report |
| Snapshot committed, `CURRENT` older | Roll forward: materialize files from blobs, set `CURRENT`, append event with `recovered: true` |
| `CURRENT` updated, event missing | Append reconstructed event with `recovered: true` |
| Last line of `events.jsonl` is not valid JSON | Move the tail to `quarantine/events.corrupt-<ts>.jsonl`; finding `state.events_truncated` (severity minor); never hide it |
| Snapshot references a missing blob | Exit 5 (corrupt state) with the list of missing blobs |

NFR-01 / T10: interruption at any step must never produce a committed snapshot whose outputs are missing, and must never duplicate a side effect.

### 5.6. Edits by the author and by the agent; the dirty set (decision 2026-10-29)

On every command `rh` compares managed files with `CURRENT`; changed files form the **dirty set**.

Two classes of managed files:

| Class | Files | Who changes them, how |
|---|---|---|
| **Content** | `text.md`, `brief.md` of units, `brief.md` of the object, `glossary.md`, notes, protocol drafts | The author directly at any time. The agent **only on the author's explicit request** (below) |
| **Controlled** | everything in `.rh/`, `object.json`, `structure.yaml`, `intake/answers.json`, `approvals/`, `materials/manifest.json`, `profiles/resolved-stack.json`, records, `summary.md` and `claims.json` (M2) | Only through `rh` commands. The agent runs those commands on the author's request or as a step of a task the author started; never by editing the file |

Agent edits of content files:
1. Allowed only when the author asked for this change in the current conversation (e.g. "shorten 1.2", "fix the terminology in chapter 2"), or the change is the direct output of a task the author started (e.g. drafting a unit he asked to draft). Without such a request the agent proposes and waits (FR-34, ADR-015 p.4).
2. For anything beyond a small local fix (more than one paragraph, any change to meaning, numbers, citations or qualifiers), the agent first shows a diff or preview and applies it after the author's OK (FR-08, FR-19a).
3. Right after editing, the agent commits: `rh checkpoint --by agent --request "<author's request, quoted or closely summarized>" [--units U…]`. The request text is stored in `operation.request` of the snapshot. Paragraph-level origin (FR-53, M2) marks the changed paragraphs `agent`, or `agent_edited_by_author` if the author changes them later.
4. Locked units (M3, FR-21) are never edited, even on request, until the author unlocks them.

Author edits: the author edits content files directly; `rh checkpoint --by human [--message]` records them. Any command that finds a dirty set without a checkpoint records it with producer `unattributed` before proceeding, so nothing is lost; status shows it so the author can attribute it.

`rh` cannot technically tell who typed a change; attribution relies on the agent following `AGENTS.md` (H13) and on the author's checkpoints. This is an audit trail, not enforcement.

### 5.7. Stage contracts

Adapted from AutoResearchClaw `StageContract` (registry #19): each stage declares `inputs` (refs that must exist and be current), `outputs` (refs it produces), `dod` (deterministic checks), `gate`, `error_codes`, `max_retries`. `rh` sets a stage `completed` only when its outputs validate — never merely because an agent said so (`06-contracts.md` v0.1).

## 6. Freshness and invalidation — M1

- Every record with `inputs` or `dependencies` is **stale** when any referenced artifact's current hash differs from the recorded `sha256`, or when any of its inputs is stale (transitive).
- Freshness is computed on demand from the current snapshot; it is never written as a stored boolean.
- Only dependents are invalidated (FR-10, T09): unrelated sources, claims and checks stay current.
- Approvals bind to `manifest_sha256` of a snapshot (and optionally to a list of artifact refs). An approval for snapshot X is never accepted as approval for snapshot Y (T09: "G3 of the old snapshot is not accepted").
- Changing the version of a rule pack makes every check that used a rule from it stale (FR-10, `02-lifecycle.md` §3А.5).
- Thesis level: a changed unit text makes its summary, the parent chapter summary and `map.md` stale (FR-47, M2).

## 7. Structure and units — M1

### 7.1. `structure.yaml`

```yaml
schema_version: "0.2"
object_id: T-2026-001
labels: {chapter: "Розділ", chapter_conclusions: "Висновки до розділу"}  # from rule pack / language defaults
units:
  - {id: U-7K2M9QXA, kind: introduction, title: "Вступ"}
  - id: U-Q4R1T8ZB
    kind: chapter
    title: "Теоретичні засади …"
    children:
      - {id: U-3MNC0P2D, kind: subsection, title: "Поняття …"}
      - {id: U-8HJK5W1E, kind: chapter_conclusions, title: null}
  - {id: U-0ZX6Y7AA, kind: conclusions, title: "Висновки"}
  - {id: U-5TT2P9CC, kind: references, title: "Список використаних джерел", generated: true}
```

| Unit `kind` | Allowed in | Folder name |
|---|---|---|
| `abstract`, `introduction`, `conclusions`, `references`, `appendices`, `section` | Top level | `NN <title>` (2-digit position) |
| `chapter` | Top level (thesis) | `NN <labels.chapter> k. <title>` (k = chapter number) |
| `subsection` | Inside a chapter | `k.m <title>` |
| `chapter_conclusions` | Last child of a chapter | `k.m <labels.chapter_conclusions> k` (m = next number after the last subsection) |

Articles use depth 1 (`section` units). There is no separate code path for articles (ADR-019 p.2).

### 7.2. Unit files

Each unit folder holds `text.md`, `brief.md`, `summary.md`, `claims.json` (FR-46). M1 creates them from templates; content arrives in M2.

`text.md` front matter (YAML):

```markdown
---
id: U-3MNC0P2D
title: "Поняття …"
kind: subsection
---
```

Invariants checked by `rh structure check` (M1): every unit in `structure.yaml` has a folder with all four files; every unit folder is in `structure.yaml`; front-matter `id` matches; front-matter `title` matches `structure.yaml` (mismatch → finding with proposed `rh structure sync`); folder names equal the computed names; IDs are unique.

### 7.3. Renumbering

`rh structure renumber` (and `move`, `add`, `remove`) computes target folder names from `structure.yaml`, then renames in two phases (all to temporary names, then to final names) inside one operation, so a crash never leaves two units with the same name. References are by ID and therefore unchanged (T50).

## 8. Rule packs — M1

### 8.1. Pack layout

```
harness/rulepacks/<pack-id>/
├── pack.yaml
└── rules/*.yaml        one or more rules per file
```

`pack.yaml`:

| Field | Rule |
|---|---|
| `id`, `name`, `version` (date `YYYY-MM-DD` or semver) | |
| `layer` | 0 core · 1 document_kind · 2 study_kind · 3 regulator · 4 venue_class · 5 venue · 6 institution · 7 author |
| `status` | `draft` / `verified` / `deprecated` |
| `applies_when` | Selector on intake answers, e.g. `{document_kind: [article]}`, `{regulator: [ua]}` |
| `description` | |

### 8.2. Rule

Extends `02-lifecycle.md` §3А.4 and ADR-012 p.3:

| Field | Rule |
|---|---|
| `id`, `pack`, `version` | |
| `key` | Composition key; rules with the same key compete (e.g. `structure.sections`, `pubplan.min_publications`) |
| `kind` | `integrity` / `counting` / `structure` / `format` / `process` |
| `applies_to` | Stage IDs, e.g. `[A11, T7]` |
| `check` | Subset of `deterministic`, `semantic`, `human` |
| `severity` | `blocker` / `major` / `minor` / `info` |
| `compare`, `value` | For strictness: `min`, `max`, `required`, `forbidden`, `equals`, `one_of`; `value` typed accordingly |
| `overridable` | Default `true`; core rules are `false` |
| `statement` | English |
| `statement_original`, `lang` | Optional original wording |
| `source` | `{title, url, evidence_level, accessed_at}` |
| `checked_at`, `valid_from`, `valid_to?`, `review_after` | Dates |

### 8.3. Composition (FR-27, T29)

1. Select packs whose `applies_when` matches the intake answers; one or more per layer.
2. Group rules by `key`.
3. If a core rule (`overridable: false`) exists for the key, it is effective; competing rules are ignored and produce a finding (`rules.core_override_attempt`, major).
4. `structure` and `format`: the rule from the highest layer wins. Two different rules for the same key on the same layer → conflict finding (blocker, location A0).
5. `integrity` and `counting`: all rules apply; the effective value is the strictest (`min` → largest value, `max` → smallest, `required` → required if any requires); the effective severity is the highest. Incomparable rules (different `compare`) → conflict finding (blocker, location A0).
6. `process`: union.
7. `evidence_level: secondary` caps effective severity at `major` (ADR-012 p.5).

### 8.4. Freshness (NFR-12, T28)

- `today > review_after` or `today > valid_to` → `expired`: every check relying on the rule returns `unknown`; verified export is blocked if the rule is required.
- `today < valid_from` → `not_yet_valid`: the rule is skipped with an info finding.
- `today` comes from an injectable clock so tests are deterministic.

### 8.5. `profiles/resolved-stack.json`

`{schema_version, resolved_at, inputs: [intake ref + sha256, pack refs + sha256], packs: [{id, version, layer, status, sha256}], rules: [{rule_id, pack, key, effective, overridden_by?, freshness, effective_severity, effective_value}], findings: [ids]}`.

## 9. Intake, materials, approvals, findings, checks

### 9.1. Intake — M1

`harness/intake/questions.yaml`: questions Q1–Q10 and sub-questions from `02-lifecycle.md` §3А.2 as data:

| Field | Rule |
|---|---|
| `id` | `Q1`, `Q3a`, … |
| `core` | `true` for the ≤10 core questions (NFR-15) |
| `text` | `{uk, en}` map (§1.6); the agent asks it in the conversation language, `rh` shows it in `ui_language` |
| `help` | `{uk, en}` — one or two sentences: why the question matters and what "don't know" means for this question |
| `type`, `options` | `choice`, `multi`, `text`, `date`, `bool`, `list` |
| `condition` | Expression over earlier answers (small safe evaluator: `and`, `or`, `not`, `==`, `in`) |
| `prefill_from` | e.g. `author.profile.orcid`, `previous_intake.Q6` |
| `unknown_consequence` | `{blocks: [stage or gate IDs], unknown_checks: [rule keys], note}` |
| `modes` | Modes in which the question is asked (`revise` and `respond_to_reviewers` get the short set) |

`intake/answers.json`: `{base…, mode, answers: {Qx: {value | "unknown", source: asked|prefilled_author|prefilled_previous|derived_from_material, confirmed: bool}}, consequences: [{question, blocks, unknown_checks, note}]}`. `intake/summary.md` is rendered from it for the G0 decision.

### 9.2. Materials manifest — M1 (FR-36)

`materials/manifest.json` entries: `{id M-…, kind: file|bibtex|ris|doi_list|url_list|manuscript|dataset|git_repo|notes, path?, locator?, sha256, origin: {provided_as, original_name, provided_at}, permissions: {external_api: allowed|forbidden|unknown, personal_data: true|false|unknown, coauthor_unpublished: true|false|unknown, private: bool}, records?: [{bib_key, doi?, metadata_status, duplicate_of?}], notes?}`. Duplicates are linked, not merged. A DOI that cannot be resolved offline stays `unresolved`; network lookups (M2) set `matched`, `not_found` or `lookup_failed`.

### 9.3. Approvals — M1 (FR-35, T37, ADR-015; explanations — decision 2026-10-29)

**Gate definitions** (`harness/gates/<gate>.yaml`, data, texts as `{uk, en}` maps): `gate`, `title`, `purpose` (what this decision means in one paragraph), `what_to_check[]` (3–7 concrete items, e.g. for G0: "topic and research question are worded as you mean them", "target venue and language are right", "each 'unknown' and its consequence is acceptable for now"), `if_approved`, `if_rejected`, `if_conditions`, `reversible` (how to change the decision later), `typical_time` (e.g. "5–10 minutes"). M1 writes all five (G0, G1, G2, G3, GE); only G0 is used in M1.

**Briefing.** Every approval request renders `approvals/requests/AR-NNNN.md` in the author's `ui_language` from the gate definition and the object's data:

```
# <gate title> — <object title>
What you are deciding: <purpose>
What is being approved: <summary of the target: e.g. intake answers, unknowns and consequences; link to intake/summary.md>
What to check: <checklist>
If you approve / reject / approve with conditions: <consequences>
Can it be changed later: <reversible>
How to record the decision:
  1. Open your own terminal (not the agent's shell).
  2. Run:  rh --object <ID> gate record <GATE>
  3. rh shows this summary and asks, one at a time: decision (1 approve / 2 reject / 3 approve with conditions),
     reason (required for 2 and 3), and the confirmation code <GATE>-<6 hex>.
  4. After recording, return to the agent and say "continue".
```

`rh gate explain <GATE|AR-ID>` prints the briefing (read-only; agents may call it).

Approval request (written by agent or tool): `{id AR-…, gate, target: {snapshot_id, manifest_sha256, refs[]}, summary_path, briefing_path, status: open|answered|withdrawn}`.

Approval record (`approvals/approvals.jsonl`): `{id AP-…, request_id?, gate, target, decision, conditions?, reason, actor_role, actor_label, channel: tty_confirmation|external_document, document?: {path, sha256, description, date}, producer: {kind: human, …}}`.

Rules enforced in code:
1. `rh gate record` writes an approval only from an interactive terminal: stdin and stdout are TTYs **and** the user types back a confirmation code that `rh` shows (gate + last 6 hex chars of the target manifest hash). Otherwise it creates or updates an approval *request* and exits 3 with the briefing path and the exact command for the author. The check goes through one injectable function so tests can simulate both cases.
1a. In the interactive flow `rh` first prints the briefing, then asks for the decision, the reason and the code as numbered prompts in `ui_language`; flags (`--decision`, `--reason`, `--conditions`) only prefill the prompts, the code is always typed. Wrong code → nothing is recorded, the prompt explains what to type. If the target snapshot changed since the request, `rh` says so and shows what changed before asking.
2. `rh gate record` refuses when `RH_AGENT_SESSION` is set; host adapters set it for agent shells (M1-14).
3. `actor_role` other than `author`/`co_author` requires `--document <path>`; the document is hashed and stored as `stored=false` if gitignored.
4. Approvals are append-only; a correction is a new record that references the old one.
5. This is an audit record, not cryptographic protection against someone with full disk access (`06-contracts.md` v0.1).

Finding resolution (`accepted` / `rejected` with reason) follows the same TTY rule (M3).

### 9.4. Findings and check runs — M1 def, impl grows per milestone

Finding: `{id F-…, check_id, rule_id?, severity, status, location: {ref, unit_id?, locator?}, observed, expected, reason, evidence_refs[], proposed_action, check_run_id, resolution?: {decision, reason, by, at}}` — every field required except those marked `?` (NFR-03).

Check run: `{id, checks: [{id, version}], snapshot_id, inputs, coverage: {denominator, checked, pass, fail, unknown, not_applicable}, results: [{check_id, item_ref, result, finding_id?}], started_at, finished_at, tool_failures[]}`. The denominator is the full population, never only the checked subset (FR-09, N3).

## 10. Models — M1 (FR-55, ADR-020)

`harness/config/roles.yaml`: `{role: model_tier}` — researcher, analyst, integration_critic → `flagship`; writer, unit_critic, chapter_critic, orchestrator → `strong`; summarizer, triage, classifier → `fast`; CLI checks → `none`.

`harness/config/model-tiers.yaml`:

```yaml
schema_version: "0.2"
hosts:
  claude-code:
    flagship: {model: claude-fable-5-1}
    strong:   {model: claude-opus-5-5}
    fast:     {model: claude-sonnet-5-5, alternatives: [claude-haiku-5-5]}
  codex:
    flagship: {model: unknown}   # verify in M3 (06-research-agent §2)
```

Model call record (`.rh/model-calls.jsonl`): `{id mc-…, at, host, role, tier_required, model_id, downgrade?: {from_tier, to_tier, reason}, purpose, context_pack?, tokens_in, tokens_out, cost, duration_s, status: ok|failed, operation_id?}`. Unknown usage is the string `"unknown"`, never `0` (NFR-05).

No silent downgrade: `rh model resolve --role R` returns the model or exits 3 if the tier maps to `unknown`; a downgrade must be recorded with `rh model downgrade --role R --to <tier> --reason …` before the agent uses a lower-tier model.

## 11. Migrations — M1 (NFR-10, T40)

- Each schema has a version; `rh migrate --to <v>` transforms the **current** state into a new snapshot.
- Migrations never rewrite existing snapshots or blobs; tagged snapshots (`submitted`, `published`) keep their hashes forever.
- Each migration is a pure function `old record → new record` with a unit test and an entry in `MIGRATIONS.md`.

## 12. Evidence family and claims — contracts M1, behaviour M2–M3, M6

Defined now so the state engine is generic; behaviour arrives with the named milestone.

| Entity | Key fields | impl |
|---|---|---|
| Source | `title, authors[{family, given, orcid?}], year?, container?, volume?, issue?, pages?{first,last}, doi?, url?, issn[], language?, type, identifiers{openalex?, s2?, eric?, isbn?}, metadata_status, metadata_sources[{resource, record_id, retrieved_at}], access_level, fulltext?{local_path, sha256, license?, version: published|accepted|preprint|unknown, obtained_via}, page_map?{pdf_to_printed_offset | explicit[]}, retraction{status, checked_at, source}, links[{relation: duplicate_of|preprint_of|published_version_of, source_id}], bib_key` | M2 |
| Excerpt | `source_id, source_sha256, text (exact), locator{pdf_page?, printed_page?, section?, paragraph?, char_start?, char_end?, table?}, access_level, extraction_method: manual|pdf_text|ocr|api_abstract, quote_check{result, checked_at}` | M2 |
| Synthesis matrix row | `source_id, question_id, statement, data_basis, limitations, excerpt_ids[], position?` | M2 |
| Premise / Definition | `kind: premise|definition, term?, statement, excerpt_ids[]` **or** `assumption: true` (one of them required) | M2 |
| Dataset | `name, version, url, terms{text_or_url, verified_at}, downloaded_at, sha256, variables_doc, storage: copy|no_copy, synthetic: bool` | M3 |
| Run | `origin, status, protocol_ref, code{path, sha256}, data[{dataset_id, sha256}], env{lockfile_sha256, python, platform}, config_sha256, seeds[], argv[], network: disabled|allowed, started_at, finished_at, exit_code, outputs[{path, sha256}], missing_fingerprints[]` | M3 (analysis), M6 (ML) |
| Result row | `run_id, dataset_id, subset, condition, variable_or_metric, value, unit, aggregation, weights, n?, uncertainty?{method, value}, output_locator` | M3 |
| Claim | `unit_id, text, kind: external|own_numeric|interpretation|hypothesis|definition|premise|novelty, materiality: critical|material|background, location{unit_id, paragraph_id?, char_start?, char_end?, text_sha256}, evidence[{type, id}], support, assessments[{support, rationale, by, at, check_run_id?}], expected_tuple? (required for own_numeric), result_ref? (required for own_numeric), dependencies[]` | M2 (ledger), M3 (tuple) |
| Paragraph map | `unit_id, paragraphs[{id, sha256, origin, history[]}]` — anchor format decided in M2 [P: invisible HTML comment anchors] | M2 |

Rules that hold from M1: `supported` requires ≥1 evidence item and ≥1 dependency (v0.1 schema); a claim whose evidence is only `simulated` runs can never be `supported`; an excerpt with `access_level: abstract` caps support at `insufficient` unless the rule pack allows narrow abstract-level claims (D2).

## 13. Adoption record — M1 (FR-24, H4)

`harness/third_party/manifest.json` → `adoptions: [{id, origin_repo, commit (40 hex), path, license (SPDX), license_file, notice, original_copy, original_sha256, destination, adapted_sha256, mode: copy|adapt|idea, changes, acceptance_tests[], update_policy, adopted_at, adopted_by}]` (full field rules: `06-reuse-adoption.md` §2.1). `rh-dev check` verifies that every file under `third_party/` and every file with an `Adapted from` header has a record, and that the record's acceptance tests exist.

## 14. Schema inventory

| Schema file | def | impl |
|---|---|---|
| `common.schema.json` (base, refs, enums) | M1 | M1 |
| `workspace.schema.json`, `author-profile.schema.json`, `author-version.schema.json` | M1 | M1 |
| `object.schema.json`, `structure.schema.json`, `unit-frontmatter.schema.json` | M1 | M1 |
| `snapshot.schema.json`, `event.schema.json`, `lock.schema.json` | M1 | M1 |
| `rulepack.schema.json`, `rule.schema.json`, `resolved-stack.schema.json` | M1 | M1 |
| `intake-questions.schema.json`, `intake-answers.schema.json`, `materials-manifest.schema.json` | M1 | M1 |
| `approval-request.schema.json`, `approval.schema.json`, `gate-definition.schema.json`, `finding.schema.json`, `check-run.schema.json` | M1 | M1 |
| `i18n-catalog.schema.json` | M1 | M1 |
| `roles.schema.json`, `model-tiers.schema.json`, `model-call.schema.json` | M1 | M1 |
| `adoption-manifest.schema.json`, `envelope.schema.json`, `status-report.schema.json` | M1 | M1 |
| `source`, `excerpt`, `matrix-row`, `premise`, `claim` (v0.2), `paragraph-map` | M1 | M2 |
| `dataset`, `run`, `result-row` | M1 | M3 |
| `context-pack`, `summary`, `search-log`, `search-plan`, `lab-journal`, `protocol`, `brief`, `handoff` | M2 | M2 |
| `review-request`, `verdict` (v0 in M2, full in M3) | M2 | M2–M3 |
| `submission-record`, `publication-record`, `ai-use-record`, `asset`, `dispute`, `overlap-report`, `venue-check`, `style-profile`, `errors-profile`, `lock`, `budget` | M3 | M3 |
| `thesis-index`, `publication-plan`, `contribution-map`, `volume`, `own-text-import` | M4 | M4 |
| `ml-protocol` | M6 | M6 |
