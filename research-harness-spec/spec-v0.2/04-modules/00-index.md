# 04 — Module Contracts: Index

Each module file uses the same sections: **Milestone(s)** · **Requirements** · **Purpose** · **Owned files** · **Commands** · **Data contracts** · **Invariants** · **Checks** · **Reuse** · **Tests** · **Open points**. Data shapes are defined once in `02-data-model.md`; module files reference them and add only module-specific fields. Reuse details are authoritative in `06-reuse-adoption.md`.

Check kinds: **D** deterministic (CLI, no LLM) · **S** semantic (model, advisory, with rationale) · **H** human decision.

| Module file | Package(s) | Milestone | Main requirements |
|---|---|---|---|
| `state.md` | `core/`, `state/`, `validate/`, `migrate/` | M1 | FR-10, FR-11, NFR-01, NFR-02, NFR-07, NFR-10 |
| `workspace-structure.md` | `workspace/`, `structure/` | M1 | FR-42, FR-44, FR-46, NFR-14 |
| `intake-rules.md` | `intake/`, `materials/`, `rules/` | M1, M2 (packs), M3 (freshness before G3) | FR-01, FR-26, FR-27, FR-36, NFR-12, NFR-15 |
| `gates-lifecycle.md` | `gates/`, `lifecycle/` | M1, M3 (G1–G3, GE, records) | FR-28, FR-33, FR-35, FR-41 |
| `models-budget.md` | `models/`, `budget/` | M1 (tiers), M2 (call log in use), M3 (budget) | FR-13, FR-55, NFR-05, ADR-017 |
| `sources-library.md` | `sources/`, `library/` | M2 | FR-02, FR-03, FR-20, FR-54 p.1–2 |
| `research-lab.md` | `lab/` | M2 | FR-04, FR-29, FR-54 p.3, p.5, FR-56 |
| `claims-text.md` | `claims/`, `units/`, `provenance/` | M2 | FR-07, FR-08, FR-22, FR-45, FR-52, FR-53 |
| `summaries-context.md` | `summaries/`, `context/` | M2 | FR-47, FR-48, NFR-16 |
| `docx.md` | `export_docx/`, `import_docx/` | M2 (export), M3 (import) | FR-12 (draft), FR-43 |
| `review.md` | `review/` | M3 | FR-07, FR-09, FR-14, FR-23, FR-49, FR-58 |
| `integrity.md` | `integrity/` | M3 | FR-12, FR-16, FR-17, FR-19, FR-30, FR-32, FR-37, FR-51, NFR-06, NFR-11 |
| `lifecycle-records.md` | `records/`, `lifecycle/` (M3 part) | M3 | FR-21, FR-28 (records), FR-31, FR-33, FR-34, FR-41 (revise, reviews) |
| `analysis-sandbox.md` | `analysis/` | M3 | FR-05, FR-06, FR-18, FR-39, FR-54 p.4, FR-57, FR-59 |
| `thesis.md` | `thesis/` | M4 | FR-15a, FR-15b, FR-50 |
| `ml.md` | `ml/` | M6 | FR-04 (ML), FR-05/06 (ML runs) |

## Dependency rules

- Lower rows may import upper rows' public APIs; never the reverse (`state` imports nothing above it).
- Every module writes object state only through `state.operation()` (02 §5.3). No module writes files in an object folder directly.
- Network access is allowed only in `sources/adapters/` (and, from M3, in the Codex-critic subprocess wrapper in `review/`), and only after the source policy and `budget.check()` allow it (ADR-016, ADR-017). Every other module works offline. The analysis sandbox runs with network off (FR-39).
- Modules never call an LLM. Semantic checks are executed by host agents; modules prepare inputs (context packs) and validate and store outputs (handoffs, findings, assessments).
