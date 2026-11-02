# M3-14 — Repository / PR check and injection handling

> Milestone M3a. Module `integrity.md`. Requirements FR-16, NFR-06, NFR-11.
> Tests T41 (repo), T14 (injection). Base `main`.

## Goal

Keep secrets, foreign material and holdout out of git, and treat injected
instructions as data — enforced deterministically before anything leaves the
harness.

## What this card delivers

- **`integrity/repo.py`** (core, LLM-free) — the full repository / PR check:
  - forbidden paths (holdout, foreign full texts, private, `.env`,
    `*.local.yaml`, secrets dirs, object work/staging — 01 §5);
  - `holdout_hash_hits` — any tracked file whose SHA-256 is in
    `harness/evals/holdout.lock.json` (content copied out of holdout);
  - `secret_hits` — API-key / private-key / bearer / `*_KEY=` / token-URL
    patterns in text files; **holdout paths are never read (H1)**;
  - `run` + `findings_from` → `repo.forbidden_path` / `repo.holdout` /
    `repo.secret`, all blocker (NFR-11).
- **`rh repo check [--staged]`** — runs the check over tracked (or staged)
  files; exit 3 when anything is blocked.
- **`rh-dev check`** now calls `integrity.repo.run` for its repo step, so the
  gate and the CLI share identical logic (secrets + holdout hashes added to the
  gate). The old `research_harness_dev.check` names are re-exported.
- **`integrity/injection.py`** — `scan(text, location)` → `integrity.prompt_injection`
  (major) for imperative patterns ("ignore previous", "you are now", reveal/send
  secret, token-bearing URLs; Ukrainian included). Content is data, never
  executed (H10); reusable by the DOCX import (M3-09) and import flows.

## H5 note

The spec lists `repo_check.py` under `research_harness_dev`, but the core CLI
`rh repo check` cannot import `research_harness_dev` (H5). The logic therefore
lives in `research_harness.integrity.repo`; `research_harness_dev.check` imports
it (dev → core is allowed), satisfying both the spec's "same logic in the gate"
intent and H5.

## Not in this card

Wiring `injection.scan` into the `.docx` import path (M3-09) and web/import
adapters; dataset `storage: no_copy` enforcement (sandbox, M3-18). Full-text
source scanning already exists (`source.injection_suspect`, M2).

## Tests

`tests/unit/integrity/test_repo.py` (forbidden paths, secret hit + holdout-path
skip, holdout-hash hit, blocker findings) and `test_injection.py` (English +
Ukrainian imperatives, token URL, clean text). `rh repo check` runs clean over
the 720 tracked repo files. Full `rh-dev` gate green.
