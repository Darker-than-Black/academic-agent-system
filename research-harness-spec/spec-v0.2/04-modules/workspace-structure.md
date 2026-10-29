# Workspace, author level, document structure

**Milestone(s).** M1 (cards M1-06, M1-07); M2 adds `map.md` / `glossary.md` (see `summaries-context.md`).

**Requirements.** FR-42, FR-44, FR-46, NFR-14; ADR-011 rev.2, ADR-014 rev.2, ADR-019 p.1–2.

**Purpose.** Where things live and in which order: the `Projects/` workspace, the author level `_author/` with versioned data, one folder `Title__ID` per article or thesis, and the unit tree of each document.

**Owned files.** Workspace: `.rh-workspace.json`, `_author/**`. Object: `object.json` (identity part), `structure.yaml`, `manuscript/**` folder layout and unit templates. Harness: `research_harness/{workspace,structure}/`, `harness/config/labels.yaml`.

**Commands.** `rh init-workspace`, `rh workspace reindex`, `rh author show|set|add-publication|add-corpus|pin`, `rh rename`, `rh structure show|add|move|retitle|remove|renumber|check|sync`.

**Data contracts.** 01 §4; 02 §3 (workspace, author, pins), §4.1 (object), §7 (structure, units, renumbering).

**Invariants.**
1. ID is the key of every reference; titles and folder names are for people and may change (FR-42).
2. No object reads or writes another object's folder (ADR-011 rev.2 p.1). Shared data is only `_author/`.
3. Objects pin versions of author data; they never follow a live link (FR-44).
4. `structure.yaml` is the only source of order and hierarchy; folder names are computed from it (FR-46).
5. Renames are two-phase inside one operation (02 §7.3).
6. All names NFC; forbidden characters removed; title part ≤ 60 characters (01 §4).

**Checks.**

| ID | Kind | Severity | Source |
|---|---|---|---|
| `structure.folder_missing`, `structure.folder_unlisted` | D | blocker | 02 §7.2 |
| `structure.id_mismatch`, `structure.id_duplicate` | D | blocker | 02 §7.2 |
| `structure.title_mismatch` | D | minor (proposes `rh structure sync`) | 02 §7.2 |
| `structure.name_not_computed` | D | major (proposes `rh structure renumber`) | 02 §7.2 |
| `structure.kind_not_allowed` | D | blocker | rule packs `article`, `thesis` |
| `workspace.index_mismatch` | D | minor (proposes `rh workspace reindex`) | 02 §3.1 |
| `author.pin_outdated` | D | info | 02 §3.2 |

**Reuse.** None.

**Tests.** T45, T50, T27 (prefill from author level); fixtures F5f, F7 skeleton.

**Open points.** None.
