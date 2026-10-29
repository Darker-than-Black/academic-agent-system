# 03 — CLI `rh`

Sources: v0.1 `06-contracts.md` (envelope, exit codes), `02-lifecycle.md` §5 and §8.3, FR-41, ADR-002, ADR-015, ADR-017, ADR-019, ADR-020.

`rh` is the only component allowed to change object state. Host adapters, skills and subagents call it. `rh-dev` is a separate entry point for repository checks and fixture generation; it is never needed by end users.

## 1. Global behaviour

```
rh [--workspace PATH] [--object ID|TITLE-FRAGMENT] [--format json|text] [--lang uk|en] [--clock ISO-DATE] <command> [args]
```

| Option | Rule |
|---|---|
| `--workspace` | Else `RH_WORKSPACE`, else nearest parent with `.rh-workspace.json` |
| `--object` | Else the object folder containing the current directory; a title fragment must match exactly one object, otherwise exit 2 with candidates |
| `--format` | `json` (default) prints exactly one envelope on stdout; `text` prints a human summary. Logs go to stderr |
| `--lang` | Language of human-readable output; else `RH_LANG`, else `ui_language` from `_author/profile.yaml`, else `uk` (02 §1.6). JSON keys and enum values never change with the language |
| `--scratch DIR` | Delegated mode (`05-agents.md` §3): accepted only by fetch / compute commands (`rh search run`, `rh source lookup`, `rh source fetch-oa`, `rh library search`, `rh library page`, `rh quote check`); results are written as files to DIR, no lock is taken, object state is unchanged |
| `--clock` | Test-only override of "today" for rule freshness; refused unless `RH_TEST_MODE=1` |

### 1.1. Envelope

Every command prints one JSON object (schema `envelope.schema.json`):

```json
{
  "schema_version": "0.2",
  "command": "status",
  "status": "ok",
  "lang": "uk",
  "message": "Анкету збережено. Потрібне ваше погодження G0.",
  "operation_id": "op-01JB…",
  "object_id": "A-2026-001",
  "artifacts": [{"ref": "object:A-2026-001/intake", "sha256": "…", "path": "intake/answers.json"}],
  "findings": [{"id": "F-00003", "severity": "major", "check_id": "rules.expired", "reason": "…", "proposed_action": "…"}],
  "next_actions": [{"command": "rh --object A-2026-001 gate record G0", "who": "author", "why": "Підтвердіть підсумок анкети", "briefing": "approvals/requests/AR-0001.md"}],
  "usage": {"tokens": "unknown", "cost": "unknown", "duration_s": 0.4},
  "data": {}
}
```

`status` ∈ `ok`, `partial`, `blocked`, `invalid`, `failed`, `corrupt`. `operation_id` is present for mutating commands. `next_actions[].who` ∈ `agent`, `author`; an action for the author always carries `why` and, for gates, `briefing`. `message`, `why`, finding `reason` and `proposed_action` are in `lang`; everything else is the machine layer. Command-specific payload goes into `data`.

### 1.2. Exit codes

| Code | Meaning | Envelope `status` |
|---|---|---|
| 0 | Success (including `partial` for import/search) | `ok` / `partial` |
| 2 | Invalid input or usage | `invalid` |
| 3 | Blocked: gate, unknown required check, dirty overlap, human action needed, budget exhausted | `blocked` |
| 4 | Tool failure (lock held, I/O error, network failure in an adapter) | `failed` |
| 5 | Corrupt state (missing blob, invalid snapshot) | `corrupt` |

### 1.3. Mutating vs read-only

Mutating commands follow the commit protocol (02 §5.3). Read-only commands never write except recovery reports and never take the lock; they may run while another operation holds it and then report the lock.

## 2. Command inventory

M = milestone in which the command must exist. Commands of later milestones are listed so names stay stable; their exact flags are fixed in that milestone's spec.

### 2.1. Entry commands (FR-41)

| Command | M | Behaviour |
|---|---|---|
| `rh start [--kind article\|thesis] [--title T] [--mode create\|revise\|extend\|respond_to_reviewers]` | M1 | Creates a new object (or, if `--title` matches an existing one, asks one clarification via exit 2 + candidates) and opens A0. Returns the intake questions to ask (only unknown ones). Mode `revise` / `respond_to_reviewers` → M3 |
| `rh continue [--object X]` | M1 | Runs recovery, returns status and the next action; never changes content |
| `rh status [--object X] [--all]` | M1 | Status report (§3); `--all` lists all objects in the workspace with stage and blockers |
| `rh revise`, `rh reviews` | M3 | Routing for `revise` and `respond_to_reviewers` |
| `rh export --mode draft\|verified --format docx\|md` | M2 (draft), M3 (verified) | |

### 2.2. Workspace, author, object

| Command | M | Behaviour |
|---|---|---|
| `rh init-workspace PATH` | M1 | Creates `.rh-workspace.json`, `_author/` skeleton, `.gitignore` entries if PATH is inside a git repo |
| `rh workspace reindex` | M1 | Rebuilds the object index from folders |
| `rh author show` / `rh author set FIELD VALUE` / `rh author add-publication FILE.bib` / `rh author add-corpus FILE [--published] [--private]` | M1 | Every change appends to `_author/versions.jsonl` |
| `rh author pin [--object X] [--file profile\|publications\|…]` | M1 | Re-pins an object to the latest author version |
| `rh rename --object X --title T` | M1 | Renames folder, records history; IDs and refs unchanged (T45) |

### 2.3. Intake, rules, materials

| Command | M | Behaviour |
|---|---|---|
| `rh intake questions [--mode M]` | M1 | Returns the questions still to ask (prefilled ones are marked; T27) |
| `rh intake answer --file answers.yaml` / `rh intake answer Qx VALUE` | M1 | Validates answers, computes consequences of `unknown`, writes `intake/answers.json` and `intake/summary.md`, re-resolves the rule stack, opens an approval request for G0 |
| `rh rules resolve` | M1 | Writes `profiles/resolved-stack.json`; findings for conflicts, expired and secondary-source rules |
| `rh rules lint PACK_DIR` | M1 | Validates a pack against schemas and composition constraints |
| `rh rules freshness` | M1 | Lists expired / soon-to-expire rules for the object |
| `rh materials add PATH… [--kind K] [--private] [--external-api allowed\|forbidden\|unknown]` | M1 | Hashes, classifies, records permissions |
| `rh materials add --bib FILE` / `--ris FILE` / `--doi-list FILE` | M1 | Parses records; links duplicates; DOIs stay `unresolved` offline |
| `rh materials list` | M1 | |

### 2.4. Gates and state

| Command | M | Behaviour |
|---|---|---|
| `rh gate request GATE [--refs …]` | M1 | Agent-callable; creates an approval request bound to the current snapshot and renders its briefing `approvals/requests/AR-NNNN.md` (02 §9.3) |
| `rh gate explain GATE\|AR-ID` | M1 | Read-only; prints the briefing: what is decided, what to check, consequences, exact steps |
| `rh gate record GATE [--decision D] [--reason R] [--conditions C] [--actor-role ROLE --actor-label L --document PATH]` | M1 | Human-only, interactive (02 §9.3): shows the briefing, then asks decision, reason and confirmation code step by step; flags only prefill. Not interactive → exit 3, request stays open, envelope tells the author what to do |
| `rh gate list` | M1 | Requests, approvals, which snapshot each binds to, whether it is still valid for the current snapshot |
| `rh checkpoint --by human\|agent [--request TEXT] [--units U…] [--message M]` | M1 | Captures the dirty set as a snapshot. `--by agent` requires `--request` (the author's instruction behind the edit, 02 §5.6) |
| `rh resume` | M1 | Explicit recovery, including stale locks (02 §5.4–5.5) |
| `rh validate [--scope schema\|refs\|freshness\|structure\|all]` | M1 | Read-only; findings for every violation; exit 3 if any blocker |
| `rh history [--unit U]` | M1 | Snapshot list with producers and messages |
| `rh migrate --to V [--dry-run]` | M1 | 02 §11 |

### 2.5. Structure

| Command | M | Behaviour |
|---|---|---|
| `rh structure show` | M1 | Tree with IDs, folder names, files present |
| `rh structure add --kind K --title T [--parent U] [--after U]` | M1 | |
| `rh structure move U [--parent P] [--after U2\|--first]` | M1 | |
| `rh structure retitle U --title T` | M1 | |
| `rh structure remove U` | M1 | Moves the unit to `history/removed/` inside the operation; never deletes content |
| `rh structure renumber` | M1 | Recomputes folder names (T50) |
| `rh structure check` / `rh structure sync` | M1 | 02 §7.2 invariants; `sync` fixes front matter from `structure.yaml` |

### 2.6. Models

| Command | M | Behaviour |
|---|---|---|
| `rh model resolve --role R [--host H]` | M1 | Model ID for the role's tier on this host; exit 3 if unmapped |
| `rh model downgrade --role R --to TIER --reason TEXT` | M1 | Records an explicit downgrade for the next call |
| `rh model log --role R --model ID [--tokens-in N] [--tokens-out N] [--cost X] [--status ok\|failed] [--purpose P]` | M1 | Appends a model call record; missing values are `unknown` |

### 2.7. Evaluation and development

| Command | M | Behaviour |
|---|---|---|
| `rh eval run --suite M1\|M2… \| --case ID` | M1 | Runs cases from `harness/evals/cases/`; writes aggregated results to `evals/results/` |
| `rh eval report --suite S` | M1 | Gate report: per test pass/fail, metrics with n and CI |
| `rh-dev check` | M1 | Lint, tests, schema validity, forbidden imports and dependencies, adoption records, forbidden paths (baseline of T41) |
| `rh-dev fixtures generate F5a\|F5b\|F5f\|…` / `rh-dev fixtures check F…` | M1+ | Deterministic fixture generators and checks |
| `rh-dev host generate claude-code\|codex` | M2 (claude-code), M3 (codex) | Generates host files (subagents) from `roles.yaml`, `model-tiers.yaml`, `harness/prompts/`; `rh-dev check` fails if generated files are out of date (`05-agents.md` §7.1) |
| `rh-dev reuse upstream` | M2 | Lists upstream changes for adopted files since their pinned SHA (`06-reuse-adoption.md`) |
| `rh eval holdout mark-compromised` | M2 | Marks holdout aggregates as compromised (`08-evals-runbook.md`) |

### 2.8. M2 commands

Detailed behaviour: `04-modules/<module>.md`; cards: `07-milestones/M2.md`. Every `add` / `set` command takes `--file F` (JSON or YAML handoff) as the normal input.

| Area | Commands | Module |
|---|---|---|
| Sources | `rh source import --file F \| --from scopus\|wos\|scholar\|zotero\|ris\|bibtex F \| --doi D…`, `rh source lookup S… [--adapter A]`, `rh source link S1 S2 --relation R`, `rh source fulltext S --file F [--version V] [--obtained-via V]`, `rh source fetch-oa S…`, `rh source retraction-check S…` | `sources-library.md` |
| Library | `rh library index`, `rh library page S --page N [--printed]`, `rh library search Q`, `rh quote check [--unit U \| --excerpt E…]` | `sources-library.md` |
| Protocol | `rh protocol draft\|show\|freeze` (freeze opens a G1 request) | `research-lab.md` |
| Search | `rh search plan --file F`, `rh search run --adapter A --query Q`, `rh search log …`, `rh search stop --reason R --uncovered F`, `rh screen --source S --include\|--exclude --reason R` | `research-lab.md` |
| Synthesis | `rh excerpt add`, `rh matrix add\|show`, `rh premise add`, `rh positions set`, `rh gaps set`, `rh counter-evidence record --claim C`, `rh saturation check`, `rh findings set`, `rh lab journal add` | `research-lab.md` |
| Claims and text | `rh claims set U\|check [U]`, `rh brief set U\|check U`, `rh unit diff U --file F`, `rh unit write U --file F --request R`, `rh dictation import U --file F`, `rh provenance show [U]\|mark U --paragraph P --origin O` | `claims-text.md` |
| Summaries and context | `rh summary build U\|set U --file F\|check`, `rh map build`, `rh glossary add\|check`, `rh context pack U --role R [--budget N]` | `summaries-context.md` |
| Review v0 | `rh review prepare --level unit\|article --unit U`, `rh review submit REVIEW-ID --findings F --verdicts F` | `07-milestones/M2.md` M2-11; chapter / integration levels and Codex engine in M3 (`04-modules/review.md`) |
| Handoffs | `rh handoff check FILE` (read-only) | `05-agents.md` §2 |
| Export | `rh export --mode draft --format docx\|md` | `docx.md` |
| Dev | `rh-dev fixtures check F4-W` | `08-evals-runbook.md` |

### 2.9. Later milestones

Names and behaviour are defined in the module files; exact flags are fixed in each milestone's full cards.

| Area | Commands | M | Module |
|---|---|---|---|
| Review | `rh review prepare --level unit\|chapter\|integration [--engine claude\|codex]`, `rh review submit`, `rh review fulltext`, `rh review coverage`, `rh findings list\|resolve`, `rh dispute open\|add-evidence\|close` | M3 | `review.md` |
| Integrity | `rh overlap`, `rh ai-use show\|statement`, `rh asset add\|list`, `rh venue check`, `rh export --mode verified`, `rh repo check`, `rh style profile build\|propose\|accept`, `rh errors profile choose`, `rh errors check` | M3 | `integrity.md` |
| Lifecycle records and modes | `rh revise`, `rh reviews add\|table\|respond`, `rh lock`, `rh unlock` (human-only), `rh record submission\|publication`, `rh autonomy set` (human-only) | M3 | `lifecycle-records.md` |
| Word import | `rh import docx FILE` | M3 | `docx.md` |
| Budget | `rh budget show\|set\|check` | M3 | `models-budget.md` |
| Analysis sandbox | `rh dataset add`, `rh analysis init\|run`, `rh results list\|check`, `rh figure build`, `rh coding add\|summary` | M3 | `analysis-sandbox.md` |
| Thesis layer | `rh thesis index show\|set`, `rh pubplan add\|check`, `rh volume`, `rh contribution-map check`, `rh import own-text` | M4 | `thesis.md` |
| ML | `rh results import --ml`, `rh run plan\|execute`, `rh protocol revise` | M6 | `ml.md` |

## 3. Status report

`rh status` returns `data` (schema `status-report.schema.json`):

| Field | Content |
|---|---|
| `object` | ID, kind, title, folder, mode, document_kind, study_kind, languages, autonomy |
| `stage` | Current stage and the state of every stage |
| `gates` | Per gate: required?, request open?, approval valid for the current snapshot? |
| `blockers` | Findings with severity `blocker` and blocked stages with `reason` and `next_action` |
| `unknowns` | Each `unknown` intake answer or rule with its consequence |
| `dirty` | Managed files changed since `CURRENT` |
| `stale` | Count and examples of stale artifacts |
| `locks_and_recovery` | Held lock, quarantined staging, recovered operations |
| `next_action` | Exactly one recommended action with `who` |

`--format text` renders it like the illustration in `02-lifecycle.md` §8.2, in the output language (`--lang`).

## 4. Conventions for new commands

- Name pattern `rh <noun> <verb>`; entry commands are the only bare verbs.
- Every new command gets: envelope output, exit codes per §1.2, a row in this file (in the same PR), tests for success and for each blocked path, and its human-readable messages in both `i18n/uk.yaml` and `i18n/en.yaml`.
- Commands never prompt interactively except `rh gate record` and future finding resolution; everything else takes arguments or files so agents can drive it.
