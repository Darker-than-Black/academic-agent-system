# Analysis Sandbox

**Milestone(s).** M3 (local analytical runner, dataset registry, runs and result rows, tuple validators, figures from rows, qualitative document coding); M6 extends to ML runs (`ml.md`).

**Requirements.** FR-05, FR-06, FR-18, FR-39 (local part), FR-54 part 4, FR-57, FR-59; NFR-08; ADR-004, ADR-009, ADR-013, ADR-020 p.3–4. Schemas: 02 §12 (Dataset, Run, Result row, Claim `expected_tuple`).

## Purpose

Let the research agent analyse open data (e.g. PISA, TALIS, УЦОЯО open data) and public documents reproducibly: every own number in the text points to one result row through a full tuple, every figure is rebuilt from rows, nothing simulated is presented as real.

## Owned files

| Path (object folder) | Content |
|---|---|
| `analysis/pyproject.toml`, `analysis/uv.lock` | Separate `uv` project per object (own lockfile) |
| `analysis/scripts/*.py` | Analysis scripts (hash recorded per run) |
| `analysis/datasets/registry.json` | Dataset registry (FR-57) |
| `analysis/data/` | Local dataset copies — gitignored when terms forbid redistribution (`storage: no_copy`) |
| `runs/<R-NNNN>/run.json`, `stdout.txt`, `stderr.txt`, `outputs/` | Run records |
| `results/rows.jsonl` | Result rows |
| `assets/figures/<id>.{png,svg}` + `<id>.json` | Figures with source rows and script hash |
| `analysis/coding/<codebook-id>/` | Qualitative coding of public documents: `codebook.yaml`, `codes.jsonl` (each code with excerpt locator) |

## Commands

| Command | Behaviour |
|---|---|
| `rh dataset add --name … --version … --url … --terms URL\|FILE [--no-copy] [--synthetic]` | Registers a dataset; download only here; hash recorded; no terms → not admitted |
| `rh analysis init` | Per-object `uv` project with pinned base packages (pandas, numpy, scipy, statsmodels, matplotlib) |
| `rh analysis run SCRIPT [--dataset D…] [--seed N]` | Executes in the sandbox; writes Run + outputs; result rows from the script's structured output |
| `rh results list` / `rh results check` | Tuple validators over `own_numeric` claims |
| `rh figure build FIG-ID` | Rebuilds a figure from rows and script |
| `rh coding add …` / `rh coding summary` | Codebook, codes with locators, frequencies; quotes verified against document text (`sources-library.md`) |

## Data contracts

02 §12 plus:

| Record | Field | Rule |
|---|---|---|
| Run | `sandbox{network: disabled\|guard_only, timeout_s, cwd, python, lockfile_sha256}` | Every executed run |
| Run | `purpose` | `analysis` / `instrument_pilot`; `simulated` only with `instrument_pilot` (FR-59) |
| Result row | `derived?{expression, input_row_ids[], precision_policy, script_sha256}` | ADR-009 p.2–3 |
| Script output | `outputs/rows.json`: `[{dataset_id, subset, condition, variable_or_metric, value, unit, aggregation, weights, n?, uncertainty?}]` | `rh` validates and assigns IDs |
| Figure | `{id, rows[], script_sha256, data_sha256[], built_at}` | Stale when any row or data hash changes (FR-18) |

## Sandbox execution (FR-39 local, NFR-08)

- argv only (no shell); cwd `runs/<R>/work/`; read-only `analysis/data/`, `analysis/scripts/`; write only to the run folder.
- Network off during analysis [P]: Linux network namespace (`unshare -n`) when available; otherwise a Python-level guard via injected `sitecustomize`, recorded as `network: guard_only`. If neither is possible, the capability is `unavailable` — never a pretend sandbox. Docker optional [P].
- Timeout and memory limit from config; exceeded → `failed`.
- Re-run from a clean checkout with the same lockfile and data hashes → identical rows (T62); fingerprints recorded or listed in `missing_fingerprints`.

## Tuple validators (ADR-009, FR-06)

An `own_numeric` claim is supported only if: `result_ref` resolves to a current row; every `expected_tuple` field equals the row's; the number equals the row value after the declared transformation (no implicit ×100/÷100, no undeclared tolerance); units match (% ≠ p.p.). Must fail: 95 s vs 95 % accuracy; 0.125 of another metric shown as 12.5 %; % vs p.p.; a number from another subsample; unweighted vs weighted mean; a figure from old data (N2, D7, D8, F8 defects).

## Synthetic participants (FR-59)

Model-generated respondents or interviews are not data. Only `simulated` runs with `purpose: instrument_pilot`; any claim whose evidence includes such a run is blocked (T65).

## Invariants

1. No dataset without recorded terms of use enters an analysis.
2. Network off during `rh analysis run`; downloads only in `rh dataset add`.
3. Numbers in text come from rows through the renderer; a changed row makes dependants stale (02 §6).
4. `simulated` never supports a claim; `failed` never shows as `succeeded`.
5. Run outputs are immutable; a re-run gets a new run ID.

## Checks

| Check ID | Kind | Severity | Rule source |
|---|---|---|---|
| `analysis.dataset_terms_missing` | D | blocker | FR-57 |
| `analysis.network_attempt` | D | blocker (run failed) | FR-39 |
| `analysis.tuple_mismatch` | D | blocker (critical) / major | ADR-009, FR-06 |
| `analysis.implicit_conversion` | D | blocker | ADR-009, N2 |
| `analysis.unit_mismatch` | D | blocker | D7 |
| `analysis.figure_stale` | D | major | FR-18 |
| `analysis.simulated_as_evidence` | D | blocker | FR-05, FR-59 |
| `analysis.not_reproducible` | D | blocker | NFR-08 |
| `analysis.method_validity` | S (analyst) | major | ADR-010 p.3 |
| `coding.quote_mismatch` | D | major | FR-54 |

## Reuse

| # | Origin (short SHA) | License | Mode | Change | Acceptance test |
|---|---|---|---|---|---|
| 25, 26 | AutoResearchClaw `verified_registry.py`, `claim_verifier.py` (`be4ba47`) | MIT | **reject** | Own tuple validators | T05 (N2) |
| 3 | OPM `skills/audit-engine/SKILL.md` (`160df4d`) | MIT | copy + extend | Links to rows and run provenance | T05 (F8) |
| K-Dense | `statistical-analysis`, `scientific-visualization` (`5f2bc03`) | MIT | copy selectively after reading | Plots only from rows | T18, T62 |

Authoritative records: `06-reuse-adoption.md`.

## Tests

| Test | Fixture | Milestone |
|---|---|---|
| T04 (F8) | F8 | M3 |
| T05 (tuple F8) | F8 | M3 |
| T18 | F8 | M3 |
| T62 | F8 | M3 |
| T65 | F8 + synthetic answers | M3 |

## Open points

- [?] F8 dataset terms (PISA / TALIS / УЦОЯО): is a local copy allowed? If not, a synthetic set with the same variables, marked `synthetic`. The author approves the dataset.
- [P] Network isolation per OS; the author's laptop OS to confirm at the start of M3.
- [?] Ukrainian tokenization library and its license.
- [P] Bibliometrics of the literature corpus (FR-54 p.3: keyword co-occurrence, clusters, time trends) run as sandbox scripts over registry metadata — added here in M3 (`research-lab.md` open point).
