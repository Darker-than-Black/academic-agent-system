# Word export and import

**Milestone(s).** M2 (card M2-12: export, draft mode); M3 (import with tracked changes and comments; verified export — see `integrity.md` for conditions).

**Requirements.** FR-08, FR-12 (draft in M2, verified in M3), FR-43; ADR-006, ADR-019 p.6; NFR-14.

**Purpose.** Markdown units are the source of truth; the author, his supervisor and editors work in Word. Export builds one `.docx` in `structure.yaml` order, formatted by the rule pack; import brings every tracked change and comment back to the right unit as a diff, without losing any.

**Owned files.** Object: `export/<timestamp>-<mode>/` (`.docx`, `manifest.json`, `references.bib`, `gaps.md`), `history/imports/<ts>/` (original `.docx` received, parsed changes). Harness: `research_harness/export_docx/{assemble.py, pandoc.py, bookmarks.py, references.py}`, `research_harness/import_docx/{parse.py, map_units.py, apply.py}` (M3), `harness/rulepacks/<pack>/reference.docx` and `csl/<style>.csl`.

**Commands.** `rh export --mode draft --format docx|md` (M2), `rh export --mode verified …` (M3), `rh import docx FILE [--from supervisor|editor|author] [--actor-label L]` (M3).

**Data contracts.**

Export manifest: `{id, mode, snapshot_id, manifest_sha256, units: [{unit_id, order, text_sha256}], rule_stack: resolved-stack ref + sha256, style: {reference_docx, csl}, gaps: {placeholders, unsupported_claims, stale, unknown_rules}, files: [{path, sha256}], excluded: [{what, reason}]}`.

Bookmarks: each unit starts with a hidden bookmark `rh_<unit_id>` and ends with `rh_<unit_id>_end`; each paragraph carries a bookmark `rh_<PG-id>` [P] so import can map changes to paragraphs, not only to units.

References: BibTeX is the store; the reference list and in-text citations are rendered by pandoc citeproc with the CSL from the rule pack (ДСТУ 8302:2015 for `ua-fahove-b` by default, journal style when a journal pack exists) [?] — a maintained CSL for ДСТУ 8302:2015 must be found or written and tested in M2-12.

Import (M3): parse `w:ins`, `w:del`, `w:moveFrom/To`, `w:comment*` with author and date; map each change to the unit and paragraph by bookmarks; unmappable changes (e.g. bookmarks deleted by the editor) go to `history/imports/<ts>/unmapped.json` and become a blocker finding — never dropped (T46). Applying an import uses the `revise` flow: diff per unit, author accepts or rejects, origin of touched paragraphs becomes `agent_edited_by_author` / `author` per change author (FR-53).

**Invariants.**
1. Export never changes the Markdown sources.
2. Draft export always lists its gaps (placeholders, unsupported claims, stale items, unknown rules) in `gaps.md` and in the manifest; verified export (M3) refuses when any required item is open (FR-12).
3. Unit order follows `structure.yaml`; references are generated, never hand-edited in the output.
4. Every tracked change and comment from an imported `.docx` ends up mapped or in `unmapped.json`; the count of changes in = mapped + unmapped (T46).
5. Foreign full texts and private materials are never placed in the export bundle (NFR-06, `06-contracts.md` v0.1).
6. Cyrillic in headings, bookmarks (bookmark names are ASCII IDs), file names and bibliography sorts correctly (NFR-14, T43).

**Checks.**

| ID | Kind | Severity | Source |
|---|---|---|---|
| `export.gaps_present` | D | info (draft) / blocker (verified) | FR-12 |
| `export.style_missing` (no reference.docx / CSL for stack) | D | major (fallback to default style, recorded) | FR-43 |
| `export.bookmark_missing` | D | blocker | FR-43 |
| `import.unmapped_changes` | D | blocker until resolved | T46 |
| `import.count_mismatch` | D | blocker | T46 |

**Reuse.** None for code; pandoc used as an external binary (01 §3, not vendored).

**Tests.** T46 (export M2, import M3), T11 (draft in M2, verified in M3), T43; fixtures F4-W, F5d, F7.

**Open points.** [?] Availability of a CSL style for ДСТУ 8302:2015 (search Zotero style repository in M2-12; if none, write one and test against 10 reference examples from a real cat. «Б» journal). [?] Whether pandoc keeps custom bookmarks through `--reference-doc`; fallback — post-process with `python-docx`.
