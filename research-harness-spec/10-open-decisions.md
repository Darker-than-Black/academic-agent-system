# Відкриті рішення

Підтверджено користувачем: перший кейс IT/AI із кодом і власними результатами; малий harness; фінальний deliverable — специфікація для Codex або Claude Code.

Пропоновані defaults: один основний агент, Python CLI, Markdown+BibTeX, локальні файли, спочатку import results, bounded review. Це можна змінити після pilot.

| Питання | Навіщо потрібне | Чи блокує ядро |
|---|---|---|
| Яке конкретне дослідження/папка стане першим кейсом? | Реальні fixtures, критерії прийнятності | Не блокує schemas; блокує змістовний pilot |
| Який host основний: Codex чи Claude Code? | Перевірка інструкцій і доступних hooks/tools | Не блокує runtime-neutral CLI |
| Мова, журнал/установа, шаблон? | Export profile, термінологія, disclosure | Не блокує Markdown draft |
| Чи потрібне виконання нових експериментів у v1? | Sandbox, compute budget, GPU | За default імпортуємо результати |
| Які materials дозволено передавати зовнішнім API? | Lookup, extraction і модельний context | Локальний import можливий без них |
| Бюджет часу/коштів на research session? | Stop policy та A/B | До відповіді не виконувати платні runs |

Рішення фіксуються датою, підставою й наслідками. Зміна scope має оновити requirements, workflow і тести разом, а не лише prompt.
