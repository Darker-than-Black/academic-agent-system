# Контракти даних та стану

Усі записи мають `schema_version`, stable `id`, UTC `created_at`, `producer` (human/tool/model + version), `inputs` із artifact ID і SHA-256. ID не змінюється при текстовому перейменуванні; revision/hash змінюється. Path — відносний, нормалізований; traversal за межі project заборонено для managed artifacts. Джерело істини — immutable snapshot; поточні human-readable файли можуть бути відредаговані, тоді prior checks стають stale.

## Об'єкти

| Об'єкт | Обов'язковий зміст |
|---|---|
| Project | id, question, document_kind, study_kind, language, studies, current_snapshot, budget, capability report |
| Protocol | question, hypothesis або exploratory purpose, falsification criteria, datasets/splits, primary/secondary metrics, baseline, analysis plan, selection rules, resource limits, version |
| Source | title, authors, year (unknown дозволено), DOI/URL/local ID, retrieved_at, content_hash, origin, access_level, parser/version, extraction_quality, metadata_status, retraction_status+checked_at |
| Excerpt | source_id+source_hash, exact text/table region, locator (page/section/paragraph/offset), extraction method, available context; абстракт позначений abstract |
| Run | protocol_hash, code_hash/commit+dirty patch, data_hash/version, split_id, config_hash, environment, seeds, command argv, status, execution_kind, start/end, outputs hashes, exit_code, stdout/stderr |
| ResultRow | run_id, dataset_id, split_id, model/condition, metric_id, value, unit, aggregation, sample/repeat count, uncertainty method/value або null, output artifact+row locator |
| Claim | exact text, kind, materiality, manuscript locator+hash, evidence refs, support assessment, dependencies; власний numeric claim має result_ref + expected tuple |
| Finding | severity, rule_id, location, observed/expected, evidence refs, resolution, assessed_by; не лише score |
| Approval | gate, target snapshot/hash, decision, human identity label, timestamp, channel record reference; агент не може видавати себе за автора рішення |
| CheckRun | checks/version, snapshot_hash, coverage, pass/fail/unknown/NA per check, findings, started/finished, tool failures |

`null`/unknown не заповнювати правдоподібною вигадкою. Рік чи DOI можуть бути відсутні; підтримка ключового claim вимагає достатнього доказу незалежно від metadata completeness.

## Незалежні статуси

- metadata_status: `unresolved / matched / ambiguous / not_found / lookup_failed`.
- access_level: `metadata / abstract / fulltext / local_original`.
- support: `unreviewed / supported / partial / contradicted / insufficient`.
- freshness: `current / stale` — обчислюється за dependencies, не ручний boolean.
- run.status: `planned / running / succeeded / failed / cancelled / imported`.
- execution_kind: `local / external / simulated`.
- source retraction: `unknown / no_notice_found / notice_found`, із датою перевірки. `no_notice_found` не означає, що відкликання неможливе.

Однакова тема ≠ supported. Дві metadata API можуть мати спільне первинне джерело й не є незалежним підтвердженням змісту. HTTP timeout → lookup_failed, а не not_found. Abstract може підтримати вузьке явно написане твердження, але не приховані деталі методу.

## Стани workflow

Стан кожного stage: `pending / active / blocked / completed / failed / stale`. `completed` вимагає валідних виходів, а не тільки повернення LLM. `blocked` має reason і наступну дію. `failed` зберігає діагностику; retry створює новий attempt ID.

Зміна source hash → stale excerpts/assessments/claims, які від нього залежать. Зміна result row → stale claim, table, figure, draft check і G3. Зміна protocol → runs не переписуються; перевіряється відповідність новому протоколу, а попередня згода не переноситься автоматично. Незалежні джерела не перевіряються повторно без причини.

Для resumable mutation idempotency_key = hash(operation + normalized inputs + configuration). Перед повтором зовнішньої дії перевірити існуючий attempt і outputs. Якщо неможливо визначити, чи експеримент завершився, стан unknown/blocked; не запускати його повторно мовчки.

## Формат project directory

`project.json`; `brief.md`; `protocol/`; `sources/registry.json`; `sources/raw/`; `evidence/excerpts.jsonl`; `runs/<run-id>/`; `results/rows.jsonl`; `claims/ledger.jsonl`; `manuscript/`; `reviews/`; `approvals/`; `state/snapshots/`; `state/events.jsonl`; `exports/`.

Пакет експорту включає manifest hashes, manuscript, bibliography, findings/coverage, protocol, claim/evidence map, reproduction instructions та дозволені outputs. Повні сторонні PDF і чутливі дані не включаються автоматично; посилання/локальний locator і дозволені витяги зберігаються. Відсутні для передачі матеріали явно перелічені.

## Tool envelope і CLI

Кожна команда повертає JSON: `status`, `artifacts`, `findings`, `next_actions`, `usage`, `operation_id`. Exit codes: 0 successful operation; 2 invalid input; 3 blocked gate; 4 tool failure; 5 corrupt state. `status=partial` можливий для import/search, але export verified повертає 3, якщо required checks unknown.

Команди MVP: `rh init`, `rh status`, `rh source import`, `rh results import`, `rh validate`, `rh checkpoint`, `rh resume`, `rh export --mode draft|verified`. Для record approval потрібне реальне повідомлення/CLI-рішення користувача. Файл є audit record, не криптографічний захист від користувача з повним доступом до диска.

Машиночитаний приклад одного claim та його schema додаються в `examples/` і `schemas/`. Це мінімальний контракт, не повний набір schemas для всіх сутностей. Реалізація має завершити решту до роботи з real data.
