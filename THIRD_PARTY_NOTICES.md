# Third-Party Notices

Research Harness (Apache-2.0). Every adopted file has an adoption record in
`harness/third_party/manifest.json` and an entry below before it enters the
repository (hard rule H4, ADR-008, FR-24).

## ADP-001 — checksums (AutoResearchClaw)
- Source: https://github.com/aiming-lab/AutoResearchClaw @ be4ba4755bf1b52220f25e13b2293b5956590070
  path `researchclaw/hitl/checksums.py`
- License: MIT — Copyright (c) 2026 Aiming Lab
  (full text: `harness/third_party/autoresearchclaw/LICENSE`)
- Used in: `harness/src/research_harness/core/hashing.py`
- Modified: yes — kept the streaming SHA-256 read loop; added canonical-JSON
  hashing (sorted keys, no NaN/Infinity), text-file normalization (strip UTF-8
  BOM, CRLF/CR → LF), and extension-based file dispatch; dropped the
  stage-manifest helpers.

## ADP-002 — StageContract (AutoResearchClaw)
- Source: https://github.com/aiming-lab/AutoResearchClaw @ be4ba4755bf1b52220f25e13b2293b5956590070
  path `researchclaw/pipeline/contracts.py`
- License: MIT — Copyright (c) 2026 Aiming Lab
  (full text: `harness/third_party/autoresearchclaw/LICENSE`)
- Used in: `harness/src/research_harness/state/contracts.py`
- Modified: yes — kept the frozen-dataclass StageContract shape; renamed
  input_files/output_files to inputs/outputs carrying artifact refs; made DoD a
  tuple of deterministic check IDs and added a gate field; dropped the 23
  hard-coded ResearchClaw CONTRACTS (our stages are data, M1-11).

## ADP-003 — atomic checkpoint I/O (AutoResearchClaw)
- Source: https://github.com/aiming-lab/AutoResearchClaw @ be4ba4755bf1b52220f25e13b2293b5956590070
  path `researchclaw/pipeline/runner.py` (functions `_write_checkpoint`,
  `_write_heartbeat`, `read_checkpoint`, `resume_from_checkpoint`)
- License: MIT — Copyright (c) 2026 Aiming Lab
  (full text: `harness/third_party/autoresearchclaw/LICENSE`)
- Used in: `harness/src/research_harness/state/snapshot.py`
- Modified: yes — kept the temp-file-in-same-dir → fsync → atomic rename write
  pattern; replaced the per-stage checkpoint.json with a snapshot manifest and a
  content-addressed blob store; moved heartbeat metadata to the lock and resume
  resolution to `state/recovery.py`; no silent rerun of side effects.

## ADP-004 — citation existence check (OpenDraft)
- Source: https://github.com/MorMar7/opendraft-paperwriter @ 89128b30d9857cf9b871cbebc88ec07832260b9a
  path `engine/utils/citation_validator.py`
- License: MIT — Copyright (c) 2025 SCAILE Technologies GmbH
  (full text: `harness/third_party/opendraft-paperwriter/LICENSE`)
- Used in: `harness/src/research_harness/sources/existence.py`
- Modified: yes — kept only the Crossref DOI-existence and URL-status checks;
  dropped the hallucinated-citation heuristics, the citation-database driver and
  the CLI report; replaced `requests`/`utils.retry` with our injectable stdlib
  transport (no live calls in CI); timeout/5xx/429 → `lookup_failed` (never
  `not_found`, ADR-016), Crossref 404 → `not_found`, 200 → `matched`; results
  set `metadata_status` only, never `support`.
