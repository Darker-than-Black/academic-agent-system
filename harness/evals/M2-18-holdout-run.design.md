# M2-18 — Holdout run mode (ДИЗАЙН, на рев'ю)

> Чернетка картки. Коду ще нема. Після OK автора — реалізація на гілці
> `m2/M2-18-holdout-run`. Формат — як картки в `07-milestones/M2.md`.

## Проблема
`rh eval run` (`runner.run_suite`) читає кейси лише з `evals/cases/<suite>/`
усередині репо і пише **повний** звіт із поелементними `results` у
`evals/results/<suite>-<date>.json`. Для holdout це неприйнятно:
- кейси holdout у репо жити не можуть (`**/holdout/**` блокує коміт);
- поелементні results (claim, вердикт, дефект) = holdout-деталі, які не можна
  лишати на диску/комітити (runbook §9, картка M2-15 п.4; H1, H8);
- райтера `holdout-log.jsonl` і `mark-compromised` нема.

Картка M2-15 задекларувала holdout-прогін, але не реалізувала його.

## Goal
Автор прогониє F4-H зі своєї розшифрованої теки **поза репо**; у git лягають
**тільки агрегати** (без поелементних результатів).

## CLI-контракт
```
rh eval holdout run --dir <DIR> [--run <ARTIFACT>] [--lang uk]
rh eval holdout mark-compromised --reason "<текст>" [--lang uk]
```
- `--dir` — розшифрована тека пакета (напр. `~/rh-holdout-tmp/F4-H`). **Має бути
  поза git-репо** — інакше відмова (H1). Повторно використати `_inside_repo` з
  `research_harness_dev.fixtures.holdout_lock`, винести спільний guard у core.
- `--run` — host-артефакт С-прогону для семантичних кейсів (M2: перший прогін =
  report-only, без артефакту кейс PENDING, не fail — як зараз для semantic).
- Кейси беруться з `<DIR>/cases/*.yaml` (усі `set: holdout`).

## Перевірка цілісності (set hash)
1. Для кожного файлу в `<DIR>` порахувати sha256.
2. Звірити з `harness/evals/holdout.lock.json` (той самий формат, що дає
   `rh-dev fixtures holdout-lock`). Будь-яке розходження / зайвий / відсутній
   файл → відмова (набір не збігається з зафіксованим).
3. `set_hash` = sha256 від відсортованого списку `path:sha256` → один рядок у
   лог, щоб пізніший прогін доводив той самий набір.

## Вихід — `harness/evals/results/holdout-log.jsonl` (append-only)
Один JSON-об'єкт на рядок. **Лише агрегати**, жодних claim/вердикт/дефект/спанів:
```json
{"date":"2026-11-01","event":"run","fixture":"F4-H",
 "lock_sha256":"<sha256 holdout.lock.json>","set_hash":"<див. вище>",
 "model_id":"claude-fable-5-1","run_kind":"host",
 "n":{"MX":40,"MV":12,"MS":18},
 "metrics":{"MF_critical":{"false_pass":0,"target_met":true},
            "MA":{"invented":0,"target_met":true},
            "MX":{"value":0.80,"ci":[0.66,0.90]},
            "MV":{"value":0.75,"ci":[0.50,0.90]},
            "MS":{"value":0.72,"ci":[0.55,0.85]}},
 "all_pass":true}
```
`mark-compromised` дописує:
```json
{"date":"2026-11-01","event":"compromised","reason":"<текст>"}
```
`rh eval holdout report` (і gate-звіт) після рядка `compromised` позначає
попередні `run`-рядки як недійсні.

## Жорсткі інваріанти (H1/H8)
- holdout-режим **ніколи** не пише поелементний звіт у `results/` (на відміну від
  `run_suite`); лише агрегатний рядок у `holdout-log.jsonl`.
- Envelope `message`/`data` несе тільки агрегати — ні id кейсів, ні вмісту.
- `--dir` поза репо — інакше відмова; шляхи теки в комітовані артефакти не пишемо.
- `_check_no_holdout` на input-значеннях кейсів лишається.
- Агент цю команду не запускає — лише автор (H14 для gate-рішення).

## Reuse
- `holdout_lock.build_lock` / `_inside_repo` — хешування + guard (винести в core helper).
- `evals.metrics` — Wilson CI, MX/MV/MS/MF/MA (вже є, H5-чисте).
- `runner._run_semantic` / `run_case` — скоринг; обгортка стрипає поелементні поля.

## Files
- `src/research_harness/evals/holdout.py` — run + verify + aggregate + log + mark-compromised
- `src/research_harness/cli/evals.py` — підкоманди `holdout run` / `holdout mark-compromised`
- `src/research_harness/i18n/{en,uk}.yaml` — ключі повідомлень/помилок
- `harness/evals/results/holdout-log.jsonl` — створює прогін автора (комітяться лише агрегатні рядки)
- `tests/unit/evals/test_holdout_run.py` — на синтетичній темп-теці + синтетичному lock + синтетичному run-артефакті (H6; без реального holdout-вмісту)

## Depends on
M2-15 (suite runner, metrics), F4-H пакет автора (`holdout.lock.json` у репо).

## Verify (на синтетиці)
```
uv run pytest tests/unit/evals/test_holdout_run.py -q
uv run rh-dev        # повний guard
```

## DoD
- `rh eval holdout run --dir <поза-репо>` звіряє hash набору з lock, рахує агрегати,
  дописує один рядок у `holdout-log.jsonl`; поелементних результатів на диск не лишає.
- `--dir` усередині репо → чітка відмова (H1).
- `mark-compromised` дописує маркер; звіт інвалідовує попередні рядки.
- Тести зелені на синтетиці; `rh-dev check: OK`.
- PR «M2-18 holdout run mode», одна картка (H3).

## Відкриті питання (рішення автора)
1. **Форма CLI:** окрема підкоманда `rh eval holdout run` (рекомендую — holdout-шлях
   явний і аудитований) vs розширити `rh eval run --suite holdout --dir`.
2. **Розташування логу:** `evals/results/holdout-log.jsonl`, комітиться (лише агрегати) — ок?
3. **set_hash:** формула вище (sha256 від `path:sha256`-списку) підходить?
4. **M2 report-only:** семантика без host-артефакту лишається PENDING (не fail) — підтвердити.
