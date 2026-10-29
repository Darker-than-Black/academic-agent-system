# ADR-008 — Reuse-first з adoption records

Статус: прийнято 2026-10-27 (рішення координатора і автора, документ 12 §7, 2026-10-27).

## Контекст
v0.1 `IMPLEMENTATION.md` вимагав власних формулювань і обережності з чужим кодом. Addendum §10 ввів принцип reuse-first із adoption records. Документ 12 перевірив 5 репозиторіїв на рівні файлів і ліцензій; автор прийняв рішення щодо кожного.

## Рішення
1. Не писати з нуля те, що прийнятно повторно використати, адаптувати чи перенести.
2. Одиниця рішення — файл / компонент разом із контрактом, ліцензією і тестом користі: `use_dependency / vendor / adapt / reject`.
3. Погоджено: адаптувати engines open-paper-machine (#1–9, #11), без fork плагіна; перенести з AutoResearchClaw `checksums.py`, checkpoint / resume (+ `StageContract`), `cost_guard.py`, `diff_view.py`; K-Dense — усі 8 кандидатів із першоджерела, після читання вмісту.
4. Відхилено: числові валідатори AutoResearchClaw (ADR-009), `entropy.md` OpenDraft, копіювання коду AI-Scientist-v2 (ліцензія з обов'язковим disclosure), AGPL-пакет PaperQA pymupdf, `journal_quality.csv`, `external/` AutoResearchClaw.
5. Для кожного перенесеного файла — adoption record у `third_party/manifest.json` і `THIRD_PARTY_NOTICES.md`: origin URL, SHA, path, ліцензія, notices, зміни, acceptance test, політика оновлення.

## Альтернативи
- **Власна реалізація всього** — відхилено: дублювання перевіреної роботи.
- **Fork open-paper-machine цілком** — відхилено: переносить невідповідні статуси (PLAUSIBLE як «майже supported»), биті посилання на скрипти, відсутність CLI-валідації.
- **Брати все підряд** — відхилено: несумісні assumptions і відомі дефекти.

## Наслідки
- FR-24 — MUST у кожному milestone, де переноситься код.
- Перед перенесенням кожен адаптований SKILL.md переписується під наші статуси (support verdict замість relevance) і посилається на CLI-перевірки.
- Ліцензія root-репозиторію не обов'язково покриває все: ліцензія фіксується по кожному файлу.

Пов'язане: FR-24, T24, документ 12.
