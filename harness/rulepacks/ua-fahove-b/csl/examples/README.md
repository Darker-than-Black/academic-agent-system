# ДСТУ 8302:2015 CSL — validation examples (author slot, P1-2)

The ДСТУ 8302:2015 style beside this folder is an in-house clean-room **draft**.
No maintained style exists in the official CSL repository
(`citation-style-language/styles`, checked 2026-11-02). A verified export is
blocked (`export.style_unvalidated`) until the draft is validated.

To validate it, drop **real** published references here (never invented — H6):

- `references.bib` — at least 10 real references from a target cat. «Б» journal,
  in BibTeX, each with a cite key.
- `expected.jsonl` — one JSON object per line:
  `{"key": "<bibtex key>", "contains": ["<substring that must appear>", ...]}`
  listing the substrings the correctly rendered ДСТУ 8302:2015 entry must
  contain (author, title fragment, «С.» page marker, year, etc.).

With both files present and `pandoc` installed, `tests/integration/test_csl_dstu.py`
renders the references through the draft CSL and checks each expectation. Without
them the test skips. Once the rendering matches the standard, set
`validated: true` and `checked_examples` in `../dstu-8302-2015.csl.status.yaml`.
