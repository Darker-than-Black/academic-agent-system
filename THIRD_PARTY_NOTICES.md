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
