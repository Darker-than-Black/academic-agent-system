# Етапи реалізації та критерії виходу

## 0. Контекст і вимірювання

Уточнити один реальний research question, доступний repo/results і цільовий формат. Підготувати F1/F2/F3 і baseline A. Вихід: ручна еталонна розмітка та відтворювана команда baseline; не починати мережу агентів без цього.

## 1. Переносиме ядро

Реалізувати schemas, init/status, artifact hashes, snapshots, locks, read/validate. Вихід: T01, T09, T10, T15. Додаток має коректно відновлюватися без LLM.

## 2. Один наскрізний сценарій

Import sources та готових results → claim ledger → agent-written Markdown → validate → draft export. Вихід: T02, T04–T08, T11 для draft. Уже дати досліднику використати й зібрати T16; не чекати всіх фіч.

## 3. Наукові й технічні gates

Protocol revisions, G1/G2/G3, semantic evidence assessment, export verified, бюджети та приватність. Вихід: решта обов'язкових tests, F3 без тихих critical false passes. Перевірити adapter на одному host.

## 4. Реальний pilot і рішення про складність

Виконати A/B, а за потреби C; виміряти користь, не тільки успішний happy path. Закрити дефекти з найвищим ризиком. Вихід: evaluation report зі збереженими невдалими кейсами й рішення keep/simplify.

## 5. Додаткові можливості

Optional runner з жорстким бюджетом → LaTeX/PDF → другий host → report profile → thesis composition → systematic review. Кожне розширення має окремий приклад, acceptance criteria та сумісність із даними попередньої версії.

## Додатковий аудит перед запозиченням коду

Для відібраних компонентів (насамперед open-paper-machine, PaperQA і валідацій AutoResearchClaw) перевірити повний call path, default config, failure handling, відповідні тести, dependencies й ліцензії. Запускати у disposable середовищі на fixture, без секретів. Цей поглиблений adoption-аудит не потрібен для незалежного втілення загальних ідей, але потрібен перед рішенням vendor/fork. Наразі сторонній код у продукт не скопійований.

## Definition of Done MVP

Чисте встановлення, documented commands, schema/version migration policy, passing mandatory tests, usable real-case draft, provenance bundle, відновлення після збою, report витрат/невідомого, зрозумілі limitations. Відсутність доведеної користі проти baseline — причина не розширювати scope.

Оцінку календарних строків не фіксуємо до першого вертикального зрізу: головна невідомість — доступність і якість вхідних матеріалів, а не написання CLI.
