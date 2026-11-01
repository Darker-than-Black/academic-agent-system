# M2-19 — Host-прогін: вирівнювання claim_id наосліп (ДИЗАЙН, на рев'ю)

> Чернетка картки. Коду ще нема. Після OK автора — реалізація на гілці
> `m2/M2-19-host-run-alignment`. Формат — як M2-18 та картки в `07-milestones/`.

## Проблема
Семантичний скорер (`research_harness/evals/metrics.py`) зіставляє `extracted`/
`reviewed` host-артефакту з еталоном **точним збігом рядка** `claim_id`
(`C-001`…`C-044`). Але:

- `manuscript.md` claim_id **не містить** (суцільна проза);
- еталонні `claim_id` живуть лише в `annotation.yaml`, кожен зі `span`
  `{section, paragraph, start, end}` + `expected_verdict`;
- субагентам `annotation.yaml` передавати **не можна** (H6) — інакше baseline
  фіктивний.

Runbook (`evals/cases/M2-semantic/README.md` §«Форма артефакту») показує артефакт
**уже** з еталонними `claim_id`, але **ніде не описує, як вихід моделі отримує ці
id наосліп**. Це дірка: без вирівнювання агент не може зібрати валідний host-run,
а якщо вирівнює, тримаючи еталон у тому самому кроці, що й генерує вихід, —
цілісність baseline тримається лише на «не підглядаю вердикти» (ризик H6).
(Аналог gap'у holdout-run → M2-18.)

Вирівнювання потрібне **лише** для `extracted` і `reviewed`. `integration_findings`
скоряться по `defect_id` (не claim_id), `contribution_points` (MA) самопозначені
(`response == "invented"`) — їм вирівнювання не треба.

## Goal
Розділити host-прогін на два кроки так, щоб вердикти/дефекти походили **винятково**
зі сліпого прогону, а еталонні `claim_id` проставлялися **механічно** (геометрія
спанів), без перенесення жодного еталонного вердикту у вихід моделі.

## Крок 1 — сліпий прогін (оркестратор + субагенти, без annotation)
Вхід субагентів: **лише** `manuscript.md` + `sources.yaml` (метадані) + локальні
повні тексти (`<об'єкт>/sources/fulltext/*.pdf`, через `rh library`). `annotation.yaml`
**ніколи** не в контексті (H6). Послідовність (runbook §«Правила прогону» п.2):
витяг тверджень → вердикт по кожному → позначені дефекти → інтеграційна перевірка
(D13) → точки авторського внеску (T49).

Вихід — `evals/fixtures/F4W/runs/F4W-host-<дата>.raw.json`:
```json
{
  "schema_version": "0.2",
  "fixture": "F4-W",
  "run_kind": "host",
  "producer": {"model_id": "claude-fable-5-1", "date": "<YYYY-MM-DD>",
               "budget_used": "<токени|$>", "note": "roles per config/roles.yaml@<commit>"},
  "extracted": [
    {"local_id": "M-001", "material": true,
     "anchor": {"section": "Abstract", "paragraph": 1, "quote": "<verbatim речення з рукопису>"}}
  ],
  "reviewed": [
    {"local_id": "M-001", "verdict": "contradicted", "flagged_defects": ["D13"]}
  ],
  "integration_findings": [{"id": "IF-1", "defect_id": "D13"}],
  "contribution_points": [{"point_id": "CP-1", "response": "placeholder"}]
}
```
- `local_id` — внутрішній id моделі (reading order), **не** еталонний.
- `anchor.quote` — **дослівне** речення з рукопису, до якого прив'язане твердження.
  Вирівнювач резолвить його в `(section, paragraph, start, end)` тим самим
  механізмом, що `research_harness_dev.fixtures.f4w_annotation` (через
  `check.py::_paragraphs`). Якщо quote у рукописі не знайдено → твердження
  відхиляється (не вгадуємо позицію, H7).
- Вердикти/дефекти — **фактичний** вихід моделі. Еталон тут не фігурує.

## Крок 2 — механічне вирівнювання (`align`, ядро, LLM-free H5)
Вхід: `raw.json` + `annotation.yaml`. Для кожного еталонного claim беремо його
`span`; серед raw-anchor'ів у тому самому `(section, paragraph)` шукаємо той, що
**максимально перекриває** `[start, end)` за символами. Правило 1:1, жадібно за
найбільшим перекривом; поріг — див. відкрите питання 2.
- raw-твердження, що зіставилось → отримує еталонний `claim_id`;
- raw-твердження без збігу вище порога → `claim_id: null` (spurious; б'є по MX precision);
- еталонний claim без raw-збігу → просто відсутній у `extracted` (missed у MX recall).

Вихід: `evals/fixtures/F4W/runs/F4W-host-<дата>.run.json` — рівно схема
`schemas/eval_run.schema.json` (з `claim_id`), яку їсть `rh eval run --run`.
**Вирівнювач лише перейменовує** `local_id`→`claim_id`; жоден `expected_verdict`/
`defect_id` з еталону у вихід не копіюється.

### Захист від підробки (H6)
- `raw.json` фіксується чекпойнтом **до** вирівнювання; `run.json` несе
  `raw_sha256` (+ `aligned_from`). Будь-яке посмертне редагування сирого прогону
  → розбіжність хешу (як `set_hash` у M2-18).
- Оскільки вердикти вже заморожені у `raw.json`, вирівнювач **не може** протекти
  еталонний вердикт у вихід. Тому крок 2 безпечно запускати й агентові — АЛЕ
  див. відкрите питання 3 (чий це крок за H14).

## CLI-контракт (проєкт)
```
rh eval align-run --raw <raw.json> --annotation <annotation.yaml> --out <run.json> [--lang uk]
```
Далі без змін:
```
rh eval run --suite M2-semantic --run <run.json>
rh eval report --suite M2-semantic
```

## Жорсткі інваріанти
- Субагенти сліпого прогону **ніколи** не бачать `annotation.yaml` (H6).
- Вирівнювач **чисто геометричний**; переносить тільки id, ніколи вердикт/дефект.
- `anchor.quote` не знайдено в рукописі → відхилити твердження, не вгадувати (H7).
- Ядро LLM-free (H5): `align` не кличе модель.
- Рішення гейта M2 — автор (H14); агент готує звіт.

## Reuse
- `research_harness_dev.fixtures.f4w_annotation` / `check.py::_paragraphs` — резолв
  дослівного quote у `(section, paragraph, start, end)`.
- `evals.metrics` — скорери (готові).
- M2-18 `set_hash`/`_sha256` — патерн хешу-пломби.

## Files (після OK)
- `src/research_harness/evals/align.py` — резолв anchor + геометричне вирівнювання + хеш-пломба.
- `src/research_harness/schemas/eval_run.raw.schema.json` — схема сирого прогону (anchor/local_id).
- `src/research_harness/cli/evals.py` — підкоманда `eval align-run`.
- `src/research_harness/i18n/{en,uk}.yaml` — ключі.
- `evals/cases/M2-semantic/README.md` — §«Як зробити host-прогін»: додати крок raw→align→run.
- `tests/unit/evals/test_align.py` — синтетичний рукопис + синтетичний raw + синтетичний annotation (H6; без реального вмісту), включно з перевіркою «вердикт не протікає».

## Depends on
M2-15/M2-17 (scorer, eval_run), M2-16 (F4-W manuscript+annotation зі спанами).

## Відкриті питання (рішення автора)
1. **Форма anchor:** дослівний `quote` (резолвиться в span; рекомендую — стійко,
   перевіряється наявністю в рукописі) vs модель одразу віддає `{section, paragraph,
   start, end}` (крихко: моделі погано рахують офсети).
2. **Поріг збігу:** напр. ≥50% перекриву коротшого спана, 1:1 жадібно за макс.
   перекривом. Чи цей поріг/метрика ок? Що робити з нічиєю (два однакові перекриви)?
3. **Хто запускає `align-run`:** лише автор (увесь ланцюг гейта під автором, H14) vs
   дозволити агентові (вердикти вже заморожені в raw → протекти не може). Рекомендую:
   агент готує `raw.json` сліпо, автор запускає `align-run` + scorer.
4. **Кілька raw на один gold span** (модель розбила один gold-claim на два): id —
   найкращому перекриву, решта `null`. Підтвердити (впливає на MX precision).
5. **Розташування `align`:** ядро `rh eval` (поряд зі скорером, що теж читає
   annotation) vs `rh-dev` (інструмент побудови фікстури). Рекомендую ядро `rh eval`.
