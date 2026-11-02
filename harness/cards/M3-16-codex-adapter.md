# M3-16 — Codex adapter and host parity

> Milestone M3a. Module `05-agents.md` §7.2. ADR-001 p.3, NFR-13. Test T42.
> Depends on M1-14. Base `main`.

## Goal

A Codex host adapter that reads the same host-neutral `AGENTS.md`, denies the
same paths, and produces the same `rh` CLI results as Claude Code.

## H12 verification

Codex config syntax verified against the official Configuration Reference
(<https://learn.chatgpt.com/docs/config-file/config-reference>, 2026-11-02):
`sandbox_mode`, `[sandbox_workspace_write]` `network_access`, path denial via
`[permissions.<p>.filesystem] "<glob>" = "deny"`, `AGENTS.md` read natively with
`project_doc_max_bytes`, and agent env via `[shell_environment_policy]`.

## What this card delivers

- **`rh-dev host generate codex`** → generates **`harness/host/codex/config.toml`**:
  `sandbox_mode = workspace-write`, `network_access = false`, read-deny globs for
  holdout / `.env` / `*.local.yaml` / secrets / private (mirroring `rh repo
  check`), `[shell_environment_policy.set]` `RH_AGENT_SESSION=1` + `RH_HOST=codex`
  with `ignore_default_excludes = false` (secrets stay out of agent shells), and
  `project_doc_max_bytes` for the native `AGENTS.md`.
- **`harness/host/codex/README.md`** — the claude-code ↔ codex mapping and the
  defence-in-depth caveat below.
- Deterministic generator + committed-output sync test; host-parity test.

## Deny rules are defence in depth

Codex named permission profiles are beta and **Codex ≤ 0.137.0 ignores them**.
The binding guarantee stays the in-code forbidden-path check in `rh repo check` /
`rh-dev check` (H1, H8, NFR-11), identical on every host; the Codex deny globs
are a second layer where honoured.

## Not in this card

Model tiers for Codex are `unknown` (02 §10), so no subagent files are generated
— `rh-dev host generate codex` reports each role BLOCKED (T63) until tiers are
filled. The Codex critic subprocess (`rh review --engine codex`, FR-58) is M3-17.

## Tests

`tests/unit/host/test_codex.py`: config is valid TOML with the expected
sandbox/network/env/deny values; committed `config.toml` equals the generator
output; generate writes it; **`rh version` yields identical output under
`RH_HOST=claude-code` and `RH_HOST=codex`** (runtime-neutral, NFR-13/T42). Full
`rh-dev` gate green.
