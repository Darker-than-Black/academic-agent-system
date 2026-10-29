# State, validation, migrations

**Milestone(s).** M1 (cards M1-02, M1-03, M1-04, M1-05, M1-13).

**Requirements.** FR-10, FR-11, NFR-01, NFR-02, NFR-07, NFR-10; ADR-002; ASR-01, ASR-02.

**Purpose.** The only way object state changes: atomic snapshots, single writer, idempotent operations, explicit recovery, computed freshness, schema validation, migrations that never touch archived versions.

**Owned files.** Object: `.rh/` (all). Harness: `research_harness/{core,state,validate,migrate,schemas}/`, `MIGRATIONS.md`.

**Commands.** `rh checkpoint`, `rh resume`, `rh history`, `rh validate`, `rh migrate`.

**Data contracts.** 02 §1 (base, IDs, hashing, refs, paths, languages), §5 (snapshots, commit protocol, lock, recovery, dirty set and edit classes), §6 (freshness), §11 (migrations), §14 (schema inventory).

**Public API (Python, used by every other module).**

| Function | Contract |
|---|---|
| `operation(obj, command, args, write_set, request=None) -> ctx` | Context manager implementing 02 §5.3; `ctx.stage(path, content)`; `ctx.commit()` returns snapshot ID; raises `DirtyOverlap`, `LockHeld` |
| `current(obj) -> Snapshot` | Reads `CURRENT` after read-only recovery |
| `dirty(obj) -> list[path]` | 02 §5.6 |
| `freshness(obj, ref) -> "current" \| "stale"` and `stale_set(obj) -> set[ref]` | 02 §6, transitive |
| `register_check(check)` / `run_checks(obj, scope) -> CheckRun` | Validator framework (M1-03) |
| `resolve_ref(obj, ref) -> (path, sha256)` | 02 §1.4 |

**Invariants.**
1. Snapshot is the commit point; working tree and `CURRENT` are derived (02 §5.3).
2. No committed snapshot references a missing blob.
3. Same idempotency key → no second snapshot, no second side effect.
4. `freshness` is never stored.
5. Tagged snapshots and all blobs are immutable, including during migrations.
6. `research_harness` imports no LLM SDK and no host adapter (NFR-07).

**Checks.**

| ID | Kind | Severity | Source |
|---|---|---|---|
| `schema.invalid` | D | blocker | 02 §14 |
| `refs.unresolved` | D | blocker | 02 §1.4 |
| `state.blob_missing` | D | blocker (exit 5) | 02 §5.5 |
| `state.events_truncated` | D | minor | 02 §5.5 |
| `state.unattributed_changes` | D | minor | 02 §5.6 |
| `freshness.stale` | D | major (blocker when it affects a gate target) | 02 §6 |
| `paths.absolute_or_traversal` | D | blocker | NFR-02 |

**Reuse.** AutoResearchClaw #21 `checksums.py` (M1-02), #20 runner checkpoint functions and #19 `StageContract` (M1-04). Details: `06-reuse-adoption.md`.

**Tests.** T09, T10, T11 (portability), T15 (imports), T40; fixtures F5b.

**Open points.** None.
