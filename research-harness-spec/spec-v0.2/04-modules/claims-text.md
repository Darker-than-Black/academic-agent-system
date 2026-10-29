# Claims, briefs, text and paragraph provenance

**Milestone(s).** M2 (cards M2-06, M2-07, M2-10). Locked sections, `revise` / `respond_to_reviewers`, style profile, typical-errors profile, AI-use statement — M3 (`integrity.md`).

**Requirements.** FR-07, FR-08, FR-22 (briefs), FR-29, FR-45 p.1, FR-52, FR-53 (recording), FR-19a (invariants, enforced from M3); ADR-013, ADR-019 p.2.

**Purpose.** Text is written unit by unit from a brief, every material statement is a claim with evidence, the author's own position is never invented, dictation becomes text with minimal changes, and the origin of every paragraph is known.

**Owned files (per unit folder).**

| File | Content | Class (02 §5.6) |
|---|---|---|
| `brief.md` | Unit brief (below) | content |
| `text.md` | Text with front matter and paragraph anchors | content |
| `claims.json` | Claims of this unit (02 §12) | controlled |
| `provenance.json` | Paragraph map (02 §12) | controlled |
| `dictation/<ts>.{txt,md}` + original audio reference | Raw transcript, kept in history | content (raw is immutable once imported) |

Object: `claims/ledger.jsonl` (index of all claims, rebuilt from units), `history/dictation/` originals.

Harness: `research_harness/claims/{ledger.py, extract.py, support.py}`, `research_harness/units/{brief.py, write.py, anchors.py, diff.py}`, `research_harness/provenance/{paragraphs.py, dictation.py}`.

**Commands.** `rh brief set U --file F`, `rh brief check U`, `rh unit write U --file F --request "…"` (stores agent-produced text after diff preview; 02 §5.6), `rh unit diff U --file F` (preview only), `rh claims set U --file F`, `rh claims check [U]`, `rh dictation import U --file transcript.txt [--audio-ref R]`, `rh provenance show [U]`, `rh provenance mark U --paragraph PG-… --origin author|agent_edited_by_author|agent` (the author's correction of origin). Marking towards **less** AI involvement (to `author` or from `agent` to `agent_edited_by_author`) follows the human-channel rule of 02 §9.3, because it changes what the AI-use statement will say (FR-32); marking towards more AI involvement is allowed to agents.

**Data contracts.**

Unit brief (`brief.md`, YAML front matter + free text):

| Field | Rule |
|---|---|
| `unit_id`, `goal` | required |
| `claims_planned[]` | claim stubs or finding IDs to cover |
| `evidence_refs[]` | findings / excerpts / matrix rows / premises allowed |
| `target_volume` | characters with spaces (FR-50); range |
| `author_points[]` | **contribution points**: `{id, question, answer?: text, answered_by?: author, placeholder_text}` — places where the author's own view, example or decision is needed (FR-45 p.1) |
| `voice` | `I` / `we` / `impersonal` from author profile or venue pack |
| `language` | from object (`languages.main`) |
| `locked` | M3 |

Paragraph anchors: each paragraph in `text.md` starts with an invisible anchor `<!-- PG-XXXXXX -->` on its own line [P]. Anchors survive edits; a paragraph without an anchor gets one on the next `rh` operation and origin `unattributed`.

Origin rules (FR-53):

| Event | Origin |
|---|---|
| Paragraph written by the author or imported from dictation | `author` |
| Paragraph written by the agent (`rh unit write`) | `agent` |
| `agent` paragraph later edited by the author (checkpoint `--by human`, or docx import in M3) | `agent_edited_by_author` |
| `author` paragraph edited by the agent on request | `agent_edited_by_author` is **not** used; it becomes `agent` with `history` keeping the author version [P] |
| Change detected without attribution | `unattributed` until the author confirms |

Claim support rules (deterministic caps applied before any semantic verdict):

| Condition | Maximum support |
|---|---|
| No evidence | `insufficient` |
| Only abstract-level excerpts | `insufficient` (unless pack allows narrow abstract claims) |
| Evidence source `not_found` / retraction notice | `not_found` / blocker |
| Only `simulated` runs | `insufficient` |
| Quote check failed for the cited excerpt | `partial` at most, with finding |
| Topic match without explicit statement in excerpt | never `supported` (N1) |

**Invariants.**
1. A unit is written only from its brief and a context pack (`summaries-context.md`); the writer never cites a key that is not in the registry (07-components draft procedure).
2. A contribution point without the author's answer appears in the text as a visible placeholder (`[[AUTHOR: <question>]]` in the manuscript language), never as an invented position (FR-45, T49, metric MA = 0).
3. Agent text enters `text.md` only through `rh unit write` after a diff preview, on the author's request or as output of a task he started (02 §5.6, H13). Author edits are never overwritten; if the target paragraph changed since the agent read it, `rh unit write` refuses and shows a three-way diff (T07).
4. Dictation: structuring keeps the author's wording; changes are limited to punctuation, removal of repetitions and fillers, paragraph breaks and moving fragments to brief order; every changed phrase is visible in a diff; the raw transcript is kept (FR-52, T57).
5. Numbers, citations, qualifiers and limitations are preserved by any stylistic pass (FR-19a; enforced by checks from M3, recorded from M2).
6. Claims are bound to the text by paragraph ID and text hash; a changed paragraph makes its claims stale (02 §6).
7. No instruction to hide AI use or evade detectors is ever applied (N4, FR-32).

**Checks.**

| ID | Kind | Severity | Source |
|---|---|---|---|
| `brief.required_missing` | D | blocker for writing | FR-22 |
| `brief.point_unanswered` | D | info (placeholder will be used) | FR-45 |
| `text.placeholder_present` | D | major for verified export, none for draft | FR-45 |
| `text.unknown_cite_key` | D | blocker | FR-08 |
| `text.author_edit_conflict` | D | blocked | T07 |
| `claims.unbound` (claim without paragraph / hash) | D | major | FR-07 |
| `claims.material_without_evidence` | D | blocker for verified export | FR-07 |
| `claims.support_cap_exceeded` | D | blocker | rules above |
| `provenance.unattributed` | D | minor | FR-53 |
| `dictation.wording_changed` | D | info with diff (T57 metric: share of preserved phrases) | FR-52 |
| `claims.extraction_recall`, `claims.support_verdict` | S | advisory, measured (MX, MV, MF) | T06 |

**Reuse.** OPM #8 writing-engine + `/draft-section` (rewritten to briefs, claim ledger, contribution points), K-Dense `scientific-writing`, `citation-management`, OpenDraft #30 claim / citation pair structures (not the judge), OpenDraft #35 `voice.md` as idea for FR-19 (M3), AutoResearchClaw #23 `diff_view.py` for previews. Details: `06-reuse-adoption.md`.

**Tests.** T06 (baseline in M2), T07, T22 (briefs + integration, M2 report), T30, T49, T57, T58 (recording); fixtures F4-W, F6 dictations.

**Open points.** [P] Anchor format (HTML comment) — the alternative is a sidecar map by paragraph hash; HTML comments are invisible in rendered Markdown and survive pandoc export when stripped by a filter. Decide in M2-10 after the docx round-trip test.
