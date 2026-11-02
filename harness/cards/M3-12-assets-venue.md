# M3-12 — Assets and venue check

> Milestone M3a. Module `integrity.md`. Requirements FR-17, FR-37.
> Tests T17, T39. Base `main`.

## Goal

Register the rights of every asset and the indexing status of the target venue,
so a verified export can refuse an unlicensed third-party asset or an uncovered
venue.

## What this card delivers

- **`integrity/assets.py`** (core) + **`asset.schema.json`**: asset registry
  (`assets/registry.json`), `add_asset` (computes the file SHA-256, validates),
  `rights_findings` → `integrity.asset_rights` **blocker** for a `third_party`
  asset whose `rights_status` is not `licensed`/`permission_documented`;
  `permission_documented` requires a `permission_doc`.
- **`integrity/venue.py`** (core) + **`venue-check.schema.json`**: records
  `venue/checks/VC-NNN.json` (`record_check`), `status_findings` →
  `integrity.venue_status` (**blocker** if `not_included`, **major** if `unknown`
  or no check — no evidence never passes, D14).
- **`rh asset add PATH --origin … --rights … [--kind --license --source-ref
  --permission-doc --from-rows]`** / **`rh asset list`**.
- **`rh venue check --title … --resource … --status … [--date --issn --evidence
  --checked-by --rule-refs]`** — evidence URL or file (hashed when local).
- Schemas + examples (valid + 2 invalid each); i18n en+uk.

## Not in this card

Deriving a venue status from Scopus coverage years / MJL / DOAJ / Перелік and
the manual-mode query handoff (that status is supplied by the author/agent;
rule-pack `scopus-indexed`/`ua-fahove-b` thresholds are M3-23). Wiring
`rights_findings` + `status_findings` into verified export is M3-15. Figures
`generated_from_rows` are produced by the sandbox (M3-20).

## Tests

`tests/unit/integrity/test_assets.py` (ids, hash, rights blocker, own/licensed
pass, permission-doc required, missing file) and `test_venue.py` (record/list,
included passes, not_included blocks, unknown/no-check major, latest wins, bad
resource rejected). Schema examples pass. Full `rh-dev` gate green.
