# Семантичні кейси M2 (baseline на F4-W)

Семантична частина гейта M2 (`05-eval-base.md` §6, §8; `08-evals-runbook.md` §3).
На відміну від набору `M2` (детерміновані pytest-кейси, 20/20), ці кейси
оцінюють **вихід моделі** на F4-W проти еталонної анотації.

```
uv run rh eval run --suite M2-semantic
uv run rh --format text --lang uk eval report --suite M2-semantic
```

## Як це працює (ядро без LLM, H5)

1. **Хост-прогін (С)** — оркестратор запускає субагентів-виконавців на `manuscript.md`
   (витяг тверджень → вердикти → позначені дефекти → точки авторського внеску) з
   фіксованим model ID (`config/model-tiers.yaml`) і бюджетом (H9). Їхній вихід
   зводиться в **run-артефакт** за схемою `eval_run` (`run_kind: host`, записаний
   `model_id` і дата).
2. **Оцінювання** — детермінована частина в ядрі (`research_harness/evals/metrics.py`):
   MX, MV, MS, MF, MA з n і 95% інтервалом Вілсона. Ядро моделі не викликає.

Прогін на реальному артефакті:
```
uv run rh eval run --suite M2-semantic --run <шлях-до-host-артефакту.json>
```

## Поточний стан

Кейси вказують на **синтетичний** артефакт `evals/fixtures/F4W/runs/F4W-synthetic.run.json`
(`run_kind: synthetic`, H6) — він лише прогонить і перевіряє **механіку** скорера
офлайн. Це **не** baseline гейта. Для гейта потрібен `run_kind: host` із записаним
model ID (замінити `--run` або покласти host-артефакт на місце синтетичного).

| Кейс | Тест | Метрики | Жорсткий гейт M2 |
|---|---|---|---|
| T06 | T06 | MX, MV, MS, MF | **MF: 0 critical false PASS** |
| T22 | T22 | MS (D13 інтеграція) | — (baseline; поріг у M3) |
| T30 | T30 | MS (D11 концептуальний) | — (baseline; поріг у M3) |
| T49 | T49 | MA | **MA: 0 вигаданих позицій** |

MX/MV/MS на M2 — **baseline з CI** (звіт), пороги вмикаються в M3/M5 через
`thresholds:` у кейсі. MF (critical) і MA — жорсткі вже з M2.

## Як зробити реальний host-прогін (автор)

Цей розділ — для автора: агент не може зробити валідний baseline сам (повних
текстів у репо немає — H8; прогін платний/керований — H9; живить ваш гейт — H14).

### Передумови
- **Повні тексти джерел локально.** Скачайте відкриті повні тексти 12 джерел у
  `evals/fixtures/F4W/fulltext/` (поза git — там `.gitignore`). Без них рецензент
  бачить лише абстракти, і вердикти вийдуть штучно `insufficient` — це не baseline.
  Два джерела (EN4, EN5) і так лише abstract — це нормально (дефект D2).
- **Фіксовані model ID** з `config/model-tiers.yaml` + `config/roles.yaml`:
  researcher / analyst / integration_critic → flagship `claude-fable-5-1`;
  summarizer / triage / classifier → fast `claude-sonnet-5-5`. Запишіть ці ID у
  артефакт і не змінюйте між кейсами.
- **Бюджет (H9).** Увімкніть платні виклики лише з записаним дозволом і лімітом;
  cost guard зупиняє на 100%. Ніколи не вмикайте ad hoc.

### Правила прогону
1. Субагенти бачать **лише** `manuscript.md` + `sources.yaml` (метадані) + локальні
   повні тексти. **`annotation.yaml` їм НЕ передавати** — інакше baseline фіктивний
   (H6). Еталон бачить тільки скорер, уже після прогону.
2. Оркестратор проганяє витяг тверджень → вердикт по кожному → позначені дефекти →
   інтеграційну перевірку (D13) → точки авторського внеску (T49), і зводить вихід у
   артефакт `eval_run`.
3. Один прогін = одна дата + один набір model ID. Повтори для n фіксуйте окремими
   артефактами (n у звіті обов'язковий).

### Форма артефакту
Покладіть у `evals/fixtures/F4W/runs/F4W-host-<дата>.run.json`:
```json
{
  "schema_version": "0.2",
  "fixture": "F4-W",
  "run_kind": "host",
  "producer": {
    "model_id": "claude-fable-5-1",
    "date": "<YYYY-MM-DD>",
    "budget_used": "<токени або $>",
    "note": "roles per config/roles.yaml@<commit>; fast=claude-sonnet-5-5"
  },
  "extracted":   [ {"claim_id": "C-001", "material": true}, ... ],
  "reviewed":    [ {"claim_id": "C-001", "verdict": "contradicted",
                    "flagged_defects": ["D13"]}, ... ],
  "integration_findings": [ {"id": "IF-1", "defect_id": "D13"} ],
  "contribution_points":  [ {"point_id": "CP-1", "response": "placeholder"}, ... ]
}
```
`verdict` — фактичний вихід моделі (не з еталону). `claim_id` — зіставлення з
еталоном; `null` = зайве (spurious) твердження. Схема: `eval_run.schema.json`.

### Оцінювання і звіт
```
uv run rh eval run --suite M2-semantic --run evals/fixtures/F4W/runs/F4W-host-<дата>.run.json
uv run rh --format text --lang uk eval report --suite M2-semantic
```
Жорсткі ворота M2 (прогін падає, якщо не виконано):
- **MF = 0 critical false PASS** (жоден critical-claim не `supported`, де еталон інший);
- **MA = 0** вигаданих позицій внеску.

MX / MV / MS — baseline зі значенням, n і 95% CI Вілсона (лише звіт на M2; пороги
вмикаються в M3/M5). Звіт має показувати n для кожної метрики.

### Нуль вигаданих джерел у draft export
Окремо від скорера: `rh export --mode draft` на F4-W не має містити жодного
посилання, що резолвиться в `not_found`/ніщо (напр. фейковий «Петренко»,
C-022/D5). Перевірте, що список літератури draft-експорту не фабрикує записів.

## Гейт M2 — рішення автора (H14)

Агент готує звіт (`rh eval report`), автор записує рішення в
`evals/results/decisions.md`. Холдаут F4-H автор прогонить окремо (H1).
