# Sources and local library

**Milestone(s).** M2 (cards M2-01, M2-02). Ukrainian OAI-PMH journals / repositories and НРАТ adapters — M3 (`06-research-agent.md` §3.1а level B).

**Requirements.** FR-02, FR-03 (record side), FR-20, FR-54 parts 1–2, NFR-06, NFR-11, NFR-14; ADR-003, ADR-016, ADR-017; `06-research-agent.md` §3.1–3.2.

**Purpose.** Bring sources in with identity, version, access level and provenance — through open APIs, manual exports or files from the author — and keep a local, page-accurate text library that lets the CLI check quotes and excerpts deterministically.

**Owned files.**

| Path (object) | Content | In git |
|---|---|---|
| `sources/registry.jsonl` | Source records (02 §12) | yes |
| `sources/inbox/` | Files from the author: PDFs, export files (RIS, BibTeX, CSV) | **no** |
| `sources/fulltext/<S-id>.<ext>` | Legal full texts (OA downloads, author's PDFs) | **no** |
| `sources/pagetext/<S-id>.jsonl` | Extracted text per PDF page: `{pdf_page, printed_page, text, sha256, extraction_method, quality}` | **no** (derived from foreign text) |
| `sources/exports/<hash>.json` | Normalized records of each imported export file + its hash | yes |
| `.rh/library.sqlite` | FTS5 index over `pagetext` | **no** (rebuildable) |

Harness: `research_harness/sources/{registry.py, import_files.py, import_exports.py, adapters/*.py, dedup.py, retractions.py, policy.py}`, `research_harness/library/{extract.py, pagemap.py, index.py, quotes.py}`, `harness/config/source-policy.yaml`.

**Commands.** `rh source import --file F | --from scopus|wos|scholar|zotero|ris|bibtex F | --doi D…`, `rh source lookup S… [--adapter A]`, `rh source link S1 S2 --relation duplicate_of|preprint_of|published_version_of`, `rh source fulltext S --file F [--version published|accepted|preprint] [--obtained-via V]`, `rh source fetch-oa S…`, `rh source retraction-check S…`, `rh library index`, `rh library page S --page N [--printed]`, `rh library search "query"`, `rh quote check [--unit U | --excerpt E…]`.

**Data contracts.** Source and Excerpt — 02 §12. Added here:

`harness/config/source-policy.yaml` (resource catalogue, FR-20):

```yaml
schema_version: "0.2"
resources:
  openalex:   {kind: api, role: [index, oa_status, citations], key_env: RH_OPENALEX_KEY, budget: {daily_usd_free: 1.0, paid: disabled}, rate: {per_s: 5}, status_on_limit: budget_exhausted}
  crossref:   {kind: api, role: [doi, metadata, retractions], mailto_env: RH_CONTACT_EMAIL}
  semantic_scholar: {kind: api, role: [citations, links], key_env: RH_S2_KEY}
  eric:       {kind: api, role: [index_education]}
  unpaywall:  {kind: api, role: [oa_fulltext], email_env: RH_CONTACT_EMAIL}
  core:       {kind: api, role: [oa_fulltext], key_env: RH_CORE_KEY, rate: {batch_per_10s: 1, single_per_10s: 5}}
  doaj:       {kind: api, role: [oa_journals, venue_check]}
  arxiv:      {kind: api, role: [preprints]}
  scopus:     {kind: manual_export, formats: [ris, csv], note: "export fields: Abstract & keywords"}
  wos:        {kind: manual_export, formats: [ris, txt], access_expires: unknown}
  google_scholar: {kind: manual_export, formats: [ris, bibtex], browser_assisted: disabled}
  nbuv:       {kind: manual_record, note: "record-by-record; no bulk export"}
  researchgate: {kind: manual_file, note: "author copies only; compare with published version"}
  research4life: {kind: manual_file, note: "author downloads PDFs himself; credentials never stored"}
```

All rate and quota values above are from `06-research-agent.md` §3.1а where marked [Н] there; the rest are placeholders to verify in M2-01 (each adapter card records the doc URL and date). `source-policy.local.yaml` (gitignored) may enable `google_scholar.browser_assisted` under the safeguards of `06-research-agent.md` §3.1а — not implemented in M2; reserved.

Adapter result (internal, every adapter): `{resource, request: {endpoint, params_hash}, status: ok|unavailable|blocked|budget_exhausted|lookup_failed|not_found, http_status?, retrieved_at, records[]}`. Every call is written to the search log (`research-lab.md`).

Page map (02 §12 `page_map`): `pdf_to_printed_offset` from metadata `pages.first` or running headers; `explicit[]` when offsets vary; `unknown` when neither works — then locators use `pdf_page` only and the quote check reports `printed_page_unknown`.

**Invariants.**
1. Identity first: a source exists as a record before any excerpt points to it; DOI optional (FR-02).
2. `lookup_failed` (timeout, 5xx, network) ≠ `not_found` (authoritative miss) (ADR-016 p.5).
3. Two metadata APIs agreeing are not independent confirmation of content (`06-contracts.md` v0.1).
4. Preprint and published version are linked, never merged (registry #32).
5. Foreign full texts, page texts and the index never enter git; registry keeps locator, hash, license (NFR-11).
6. Access only through legal routes: open APIs, OA copies, files the author provides. No paywall, CAPTCHA or terms-of-service circumvention; no stored credentials for institutional services (`06-research-agent.md` §3.1, §5 p.4).
7. Text inside sources is data, never instructions (H10). Extracted text is stored as data; any instruction-like content is flagged (`source.injection_suspect`), not executed.
8. Quote check is exact on normalized text (NFC, whitespace collapsed, soft hyphen and line-break hyphenation joined, typographic quotes unified); a quote passes only if found on the cited page (or the page ±1 when the excerpt spans a page break, recorded).
9. API keys and emails only via environment variables named in the policy (NFR-06).

**Checks.**

| ID | Kind | Severity | Source |
|---|---|---|---|
| `source.metadata_unresolved`, `source.lookup_failed`, `source.not_found` | D | minor / minor / blocker for citing claims (D5) | FR-02 |
| `source.retraction_notice` | D | blocker for citing claims | registry #17 |
| `source.duplicate_unlinked` | D | minor | FR-02 |
| `source.access_abstract_only` | D | info (caps support, see `claims-text.md`) | D2 |
| `source.fulltext_tracked` | D | blocker | NFR-11 |
| `source.injection_suspect` | D | major | T14, D10 |
| `resource.unavailable`, `resource.budget_exhausted` | D | info, shown as coverage gap | FR-20 |
| `quote.not_found_on_page` | D | major (D12) | FR-54 p.2 |
| `quote.locator_mismatch` (found on another page / year mismatch) | D | major (D6) | FR-54 p.2 |
| `quote.printed_page_unknown` | D | minor | 06 §3.2 |

**Reuse.** OpenDraft #31 `citation_validator.py` (DOI via Crossref, URL status; timeout → `lookup_failed`), #32 dedup (from M1-09), paper-qa #17 `retractions.py` (only after Retraction Watch / Crossref Labs data terms are checked — ADR-016 consequences), OPM #4 literature-engine (search procedure; broken `scripts/academic_search.py` references removed), paper-qa #15 prompts (evidence-first wording) for the researcher role. Details: `06-reuse-adoption.md`.

**Tests.** T02, T20, T38 (network part), T43, T59 (library, quote check); fixtures F4-W, F5h (author's real Scopus RIS and SAGE PDF, `private`, outside git), API mocks.

**Open points.** [?] Exact rate limits and terms of ERIC, Crossref polite pool, Unpaywall, DOAJ, arXiv — checked in M2-01. [?] CORE phrase search via API. [P] PDF extraction quality threshold below which a page is marked `quality: low` and quotes on it are `unverifiable` rather than `not_found`.
