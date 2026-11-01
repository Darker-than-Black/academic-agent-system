# ТЗ: holdout-пакет F4-H

> Планувальний документ для автора. Сам holdout (джерела, рукопис, розмітка,
> кейси) у репозиторій **не** потрапляє — тільки `holdout.lock.json`. Агенти
> вмісту holdout не бачать ніколи (H1). Джерела специфікації:
> `research-harness-spec/stage-0/05-eval-base.md` §2–§5, §8;
> `research-harness-spec/spec-v0.2/08-evals-runbook.md` §9.

## 0. Мета і роль автора
F4-H — екзаменаційний набір для чесного виміру якості на gate-мілстоунах.
Готує **тільки автор, без участі агентів** (`05-eval-base.md` §4, §6).
На gate **M2** — перший прогін, **лише звіт**, без порогу. Пороги з M3
(recall критичних дефектів ≥ 0.85), повний критерій на M5.

## 1. Що потрапляє в git
| Артефакт | Шлях | Як |
|---|---|---|
| Lock-файл | `harness/evals/holdout.lock.json` | коміт через PR (H2) |
| Рядок метрик (після прогону) | `harness/evals/results/holdout-log.jsonl` | `rh` допише; коміт через PR |

Більше нічого. PR-перевірка блокує `**/holdout/**` і будь-який файл, hash якого є
в lock (T41, вмикається на M3).

## 2. Зашифрований архів (документи Project, поза git)
Назва в документах Project: `research-harness-spec/holdout/F4-H.age`
(ASCII-armored, `age` або `gpg`). Ключ лише в автора: не в Project, не в репо,
не в пам'яті Claude.

### Структура всередині архіву
```
F4-H/
  sources.yaml          # 12 джерел: locator + hash + ліцензія (без повних текстів, H8)
  manuscript.md         # тестовий рукопис огляду, UA + англомовна анотація
  concept.md            # концептуальний розділ (визначення/засновання, T30)
  refs.bib              # BibTeX: кирилиця + 1 дублікат + 1 битий DOI
  annotation.yaml       # еталон §5.1 — розмічає автор, руками, без агентів
  cases/                # YAML-кейси §5.2, set: holdout (T06, T22, T30, T49)
  key_works.yaml        # опц.: 5 обов'язкових робіт (recall пошуку, T60)
  injection/            # 1 штучний PDF з prompt injection, позначений тестовим
```

## 3. Вимоги до вмісту (`05-eval-base.md` §3.1–§3.2)
- **Підтема:** освітні науки, інша за F4-W (формувальне оцінювання) і за темою
  першої статті автора. Ніде в репо не записувати.
- **Джерела (12):** 6 UA + 6 EN, лише відкритий доступ (OpenAlex/ERIC/DOAJ/НБУВ);
  2 — лише abstract; 1 — журнал сумнівного статусу; 1 — PDF із prompt injection.
- **Рукопис:** 2500–3500 слів UA + EN abstract; 40–60 material claims; ~30%
  із seeded defects; плюс концептуальний розділ для T30.
- **Дефекти (D1–D14):** обов'язково явно D1, D2 (T06), D11 (T30), D13 (T22);
  решту розподілити до ~30%.

## 4. `annotation.yaml` — схема §5.1 (на кожен material claim)
`claim_id`, `span` (section/paragraph/start/end), `material`, `criticality`
(critical/major/minor), `expected_verdict`
(supported/partial/insufficient/contradicted/not_found/unverifiable),
`source_id`, `locator`, `access_level` (fulltext/abstract/metadata),
`defect_id` (D1–D14 або null), `rationale`. Плюс: список усіх material claims
(еталон recall), список integration findings (D13), опц. key_works.
На відміну від F4-W, spans розмічає автор руками.

## 5. Кейси — схема §5.2, `set: holdout`
`id`, `test`, `fixture: F4-H`, `set: holdout`, `milestone`, `kind`
(deterministic/semantic/human), `input`, `expected`, `metric`, `run`, `requires`.

## 6. `holdout.lock.json` — генерувати, не писати руками
Мінімум за §5.2/§9: `case_ids` + sha256 кожного файлу + дата. Генератор (автор
запускає на **розшифрованій** теці **поза** репо):

```
rh-dev fixtures holdout-lock --dir ~/rh-holdout-tmp/F4-H --out /path/holdout.lock.json
```

Генератор відмовляється, якщо `--dir` усередині git-репо (H1). Скопіювати
отриманий файл у `harness/evals/holdout.lock.json` і закомітити через PR.

## 7. Прогін на gate
```
mkdir -p ~/rh-holdout-tmp && cd ~/rh-holdout-tmp
age -d -i <ключ> /path/F4-H.age | tar x          # або gpg -d
rh eval run --suite holdout --cases-dir ~/rh-holdout-tmp/F4-H/cases
# rh допише агрегати в holdout-log.jsonl: n, значення, CI, hash набору, model ID, дата
rm -rf ~/rh-holdout-tmp
```
Поелементні результати не показувати нікому й не передавати агенту.

## 8. Definition of Done (M2)
- [ ] підтема обрана, ніде в репо не записана
- [ ] 12 джерел зі складом §3.2
- [ ] рукопис 2500–3500 слів + концептуальний розділ, 40–60 claims, ~30% дефектів
- [ ] D1/D2/D11/D13 присутні явно
- [ ] `annotation.yaml` повна за §5.1, розмічена вручну
- [ ] кейси `set: holdout` для T06, T22, T30, T49
- [ ] архів зашифровано, завантажено в Project, ключ лише в автора
- [ ] `holdout.lock.json` згенеровано і закомічено через PR; у git більше нічого
- [ ] перший прогін виконано, рядок у `holdout-log.jsonl` закомічено
- [ ] (gate) рішення записано у `decisions.md` (H14, автор)

## 9. Якщо holdout скомпрометовано
Вміст потрапив у репо/промпт/чат з агентом → `rh eval holdout mark-compromised`,
новий пакет за кроками вище, запис у `decisions.md` (`08-evals-runbook.md` §9).
