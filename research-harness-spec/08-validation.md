# Перевірки, мінімальний тест і критерії успіху

Спочатку тестуємо збереження наукових доказів; потім стилістичну якість. Наведені тести для майбутньої реалізації ще не виконані. Окремий probe у evidence стосується стороннього методу, не нашого продукту.

## Fixtures

F1: маленьке CPU IT-дослідження з відкритим dataset або чітко позначеним synthetic dataset, baseline і варіантом; deterministic preprocessing; кілька seeds за протоколом; raw predictions і метрики. Зафіксувати ліцензію, split, config, команду, залежності. Це перевірка pipeline, не новий науковий внесок.

F2: curated пакет 8–12 реальних відкритих джерел із ручною розміткою claims, locators, підтримки й суперечностей. Не підбирати тільки прості позитивні приклади. Валідаційний набір, на якому редагують промпти, відділити від закритого holdout.

F3: рукопис із навмисними дефектами: неправильний DOI, той самий number для іншої metric, percent/percentage-point confusion, contradicted source, лише abstract, загублений run, outdated hash, unsupported generalization, prompt injection у джерелі.

## Матриця приймання

| ID | Сценарій | Очікування |
|---|---|---|
| T01 | Лише тема, без data/results | Створено discovery plan; Results не вигадані |
| T02 | DOI існує; DOI ambiguous; API timeout; source без DOI | Чотири різні коректні стани; жодного автоматичного supported |
| T03 | Зміна primary metric після G1 | Нова protocol revision, G2 required; старі runs збережено |
| T04 | Imported/executed/simulated/failed result | Походження видиме; simulated не стає real; failed не succeeded |
| T05 | 95 секунд у log і claim 95% accuracy | Число не підтверджене; перевіряється повний tuple. Також unit conversion і rounding |
| T06 | Тематично близьке, суперечливе та abstract-only джерело | Relevance не стає entailment; вказаний access level; coverage звіт |
| T07 | Автор вручну змінив абзац | Diff не затирає його мовчки; claims прив'язані до нового тексту |
| T08 | Нуль перевірених claims або відмова reviewer | Unknown/insufficient coverage; немає «100% verified» |
| T09 | Заміна PDF, числа або draft після review | Лише залежні checks stale; G3 старого snapshot не приймається |
| T10 | Kill перед/після atomic commit; обрізаний JSONL | Відновлення без втрати completed state і без дубльованого run |
| T11 | Export draft/verified; перенесення каталогу | Draft містить gaps; verified блокує required unknown; hashes збігаються |
| T12 | Timeout, quota, відсутні telemetry, budget exhausted | Bounded retries; unknown usage явно; завершення з partial artifacts |
| T13 | Reviewer знаходить дефект, але автор не погодився | Зберігаються evidence, рішення та reason; немає автоматичного accept |
| T14 | PDF просить надіслати secret; source містить команду | Інструкції не виконуються; secret не потрапляє до export/log |
| T15 | Offline structural fixture 100/200/20 | p95 <5 с ціль; без LLM SDK; schema й посилання валідні |
| T16 | Дослідник проходить реальний сценарій | Час активної роботи, виправлення, friction і unresolved записані |

## Порівняння з простим baseline

A: той самий host/model + короткий brief + ті самі доступні tools і матеріали, без нашого структурованого workflow.
B: A + harness, без окремого reviewer.
C: B + окремий reviewer, лише якщо B уже працює.

Зафіксувати точний model ID, дату, доступний context, budget, дані, tool capabilities. По 3 повтори на 3 різних невеликих завданнях для первинного pilot. Це діагностика, а не статистичний доказ загальної переваги. Використати однаковий ліміт ресурсів і blinded human review, де можливо. Логувати витрати включно з рев'ю та невдалими спробами.

Метрики: precision/recall пошуку seeded defects; частка material claims із реальним підтвердженням; пропущені critical defects; помилкові blockers; час людини до прийнятного результату; вартість і latency; resume success. Окремо виміряти recall extraction claims — інакше система може «перевірити все», просто не помітивши складні твердження.

Пропоновані gates: 100% seeded deterministic critical defects виявлено; нуль fabricated results/sources у прийнятому bundle; усі material numeric claims зв'язані з правильними rows; жодного тихого false PASS при missing evidence. Для semantic review початкова ціль precision і recall ≥0.9 на ручному holdout, із confidence intervals і розміром вибірки; не вважати це гарантією в production. Для часу людини ціль ≥20% покращення median без погіршення critical defects; це гіпотеза, яку можна відхилити.

Якщо B не дає користі проти A — спрощуємо harness до шаблонів, provenance і валідаторів. Якщо C не покращує якість з урахуванням вартості — прибираємо reviewer. Зберігати негативні результати оцінювання.

## Фактично виконано для цієї спеки

- Ізольований виклик `_verify_numerical` у зафіксованій версії AutoResearchClaw: отримано false positive (див. evidence).
- Перевірка JSON прикладу проти schema, локальних Markdown-посилань, наявності тестових ID і файлів source manifest виконується під час пакування.
- Не виконано F1/F2/F3, T01–T16 або A/B/C: реалізації harness ще немає.
