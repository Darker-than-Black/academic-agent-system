# M3-08 — Modes, locks, records

> Milestone M3a. Module `lifecycle-records.md`. Requirements FR-21, FR-28,
> FR-34, FR-41. Tests T21, T29a, T36, T44. Depends on M3-06. Base `main`.

## Goal

Make the article a long-lived object: lock finished units, record submissions
and publications tied to a snapshot, handle reviewer comments, and return in
`revise` / `respond_to_reviewers` modes — all enforced in `rh`.

## What this card delivers

- **`lifecycle/locks.py`** + **`unit-lock.schema.json`** + **`rh lock U
  --reason R` / `rh unlock U`**: locks in `locks.json`; `assert_not_locked`
  wired into **both** unit write paths (`write_body`, `write_unit`) so any write
  to a locked unit fails with exit 3 (T21), even on the author's request;
  `unlock` is **human-only** (agent → request, exit 3).
- **`lifecycle/records.py`** + **`submission-record` / `publication-record`
  schemas** + **`rh record submission|publication`** (**human-only**): a
  SubmissionRecord needs a valid **G3** approval for the current snapshot and
  tags it `submitted:<date>`; a PublicationRecord tags `published`
  (version of record = current snapshot). Tags live in `records/tags.json`.
- **`lifecycle/reviews.py`** + **`reviewer-comment.schema.json`** + **`rh
  reviews add FILE --round --reviewer` / `table` / `respond --comment --action
  --response`**: comments `RC-NN` (open → closed with accept/partial/decline).
- **`rh revise [--from FILE.md] [--scope U…]`**: sets intake mode `revise`,
  stores the agreed scope and the `.md` original, and proposes locking the
  units outside scope (author confirms via `rh lock`).

## Deferred

- `revise --from FILE.docx` → the `.docx` import is **M3-09** (returns a clear
  block for now); `.md` works here.
- Importing a whole reviewer letter and splitting it into comments (semantic) —
  `reviews add` records one comment per file. The long-lived "A16 waiting" state
  and `rh continue` re-resolve already exist (M1); no new scheduling (FR-34).

## Tests

`tests/unit/lifecycle/test_locks.py` (lock/unlock cycle, `assert_not_locked`
blocks, write paths call it — T21), `test_records.py` (submission needs G3,
submission→publication with snapshot tags, no-snapshot blocks — T29a),
`test_reviews.py` (add/respond cycle, id increment, unknown comment — T44).
Schema examples for all four records. Full `rh-dev` gate green.
