# 08 — Evaluation runbook

Sources: `05-eval-base.md` (§2 holdout, §3 fixtures, §5 schemas, §6 metrics, §8 exit criteria, §9 pilot), `00-README.md` §4 and §6, 02 §1.6.

## 1. Commands

| Command | Purpose |
|---|---|
| `rh eval run --suite M<n>` | Runs every case of the milestone (regenerates deterministic fixtures first) |
| `rh eval run --case <ID>` | One case |
| `rh eval run --suite holdout --cases-dir <PATH>` | Holdout run by the author only; `PATH` must be outside the repo (refused otherwise) |
| `rh eval report --suite M<n> [--format text] [--lang uk\|en]` | Gate report |
| `rh eval holdout mark-compromised [--since DATE]` | Marks earlier holdout aggregates as `compromised` |
| `rh-dev fixtures generate <F…>` / `rh-dev fixtures check <F…>` | Deterministic fixture generators and checks |

The runner refuses any case path under `holdout/` inside the repo (H1).

## 2. Case format

YAML per `05-eval-base.md` §5.2 (`id`, `test`, `fixture`, `set: working|holdout`, `milestone`, `kind: deterministic|semantic|human`, `input`, `expected`, `metric`, `run`, `requires`). Location: `harness/evals/cases/M<n>/`. Holdout cases never live in the repo; only `harness/evals/holdout.lock.json` (IDs + file hashes + creation date).

## 3. Run types

| Type | Rules |
|---|---|
| Deterministic (Д) | Offline, no LLM; result pass / fail; required 100% |
| Semantic (С) | Fixed model ID per role (recorded), fixed date, budget cap per case, n stated; proportions with Wilson 95% CI; a value without n and CI is not accepted at a gate |
| Human (Л) | Author session per protocol; time and corrections recorded (MT) |

## 4. Fixtures

| Fixture | Who prepares | Generator / location | Milestone |
|---|---|---|---|
| F1, F3 | Implementer | `evals/fixtures/f1/`, `f3/` | M6 |
| F2-W | Implementer drafts, author checks | `evals/fixtures/f2w/` | M6 |
| F2-H | Author (proposal; open question in M6) | Outside the repo | M6 |
| F4-W | Prep chat proposes 12 sources and a manuscript with seeded defects; agent drafts the annotation; **author checks** | `evals/fixtures/F4W/` (locators, hashes, licenses only — no foreign full texts) | before the M2 gate (M2-14) |
| F4-H | **Author only**, no agents | Encrypted archive in Project docs; lock file in the repo | before the M2 gate (first run = report only); threshold at M3 |
| F5a–F5h | Implementer (scripted, synthetic); F5h are the author's private files outside git | `research_harness_dev/fixtures/` | with the milestone that needs them |
| F6 | Author (corpus, dictations) | `_author/corpus/`, not committed without consent | E2 / M3 baseline |
| F7 | Implementer generator + defect list D15–D21; author spot-checks | `evals/fixtures/f7/` | structure M1–M3, thesis defects M4 |
| F8 | Implementer selects a dataset with terms; author approves | `evals/fixtures/f8/` | M3 |

## 5. Metrics

As defined in `05-eval-base.md` §6: MD, MX, MV, MF, MS, MB, MC, MT, M$, MY, MU, MA. MF (false PASS) = 0 for critical claims at every gate from M2. MC: the denominator in reports equals the reference denominator.

## 6. Gate report

`harness/evals/results/M<n>-<date>.json` and a text rendering in the author's `ui_language`:
1. Milestone, date, commit, model IDs, budget used.
2. Table: test → pass / fail → evidence (command, exit code, key assertion).
3. Semantic metrics: value, n, 95% CI, threshold, met?
4. Holdout line (aggregates only, from `holdout-log.jsonl`).
5. Missed thresholds and the decision reference.

## 7. Decisions log

`harness/evals/results/decisions.md`: date, milestone, what was missed, the author's decision (improve / lower threshold with reasons / simplify), who decided. Negative results are kept (`05-eval-base.md` §1 p.5).

## 8. Holdout reminder

The chat that starts M2 (fixture preparation or the M2 gate) reminds the author **in a separate message** that he prepares F4-H himself before the M2 gate (`00-README.md` §6).

## 9. Процедура holdout для автора (українською)

> Цей розділ читаєте ви, тому він українською. Агенти не виконують жодного кроку з нього.

**Підготовка (один раз, до gate M2)**
1. Оберіть підтему освітніх наук, відмінну від F4-W (формувальне оцінювання) і від теми першої статті. Ніде в репозиторії її не записуйте.
2. Зберіть 12 джерел: 6 українською, 6 англійською, лише відкритого доступу. Серед них: 2 доступні тільки як анотація, 1 у журналі з сумнівним статусом, 1 PDF із вбудованою інструкцією для ШІ (prompt injection; можна створити штучний PDF і позначити його як тестовий).
3. Напишіть тестовий фрагмент огляду на 2 500–3 500 слів українською з англомовною анотацією. Він має містити 40–60 тверджень; приблизно в 30% закладіть дефекти D1–D14 (`05-eval-base.md` §3.2).
4. Розмітьте еталон за схемою `05-eval-base.md` §5.1. Робіть це без агентів.
5. Зашифруйте архів (`age` або `gpg`, ASCII armor) і завантажте в документи Project як `research-harness-spec/holdout/F4-H.age`. Ключ зберігайте лише у себе: не в Project, не в репозиторії, не в пам'яті Claude.
6. Створіть `harness/evals/holdout.lock.json` з ID кейсів і hash кожного файлу. Закомітьте тільки цей файл (через PR).

**Прогін (на gate M2–M5)**
1. Розшифруйте архів у тимчасову теку **поза** репозиторієм, наприклад `~/rh-holdout-tmp/`.
2. У власному терміналі (не через агента) виконайте: `rh eval run --suite holdout --cases-dir ~/rh-holdout-tmp/cases`.
3. `rh` додасть до `harness/evals/results/holdout-log.jsonl` лише агреговані метрики: n, значення, CI, hash набору, model ID, дату. Закомітьте цей рядок через PR.
4. Видаліть тимчасову теку. Поелементні результати нікому не показуйте і агенту не передавайте.

**Якщо holdout скомпрометовано** (вміст потрапив у репозиторій, промпт або чат з агентом)
1. Позначте попередні результати в `holdout-log.jsonl` як `compromised` командою `rh eval holdout mark-compromised`.
2. Підготуйте новий пакет за кроками вище.
3. Запишіть подію в `decisions.md`.
