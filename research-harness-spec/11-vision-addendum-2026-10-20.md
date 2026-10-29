# Research Harness — доповнення до бачення та реєстр повторного використання

Дата: 2026-10-20. Статус: вимоги користувача + пропозиції для обговорення. Доповнює специфікацію v0.1 від 2026-10-13; не оголошує нові архітектурні пропозиції погодженими. Старі файли не переписані. Після обговорення зміни треба інтегрувати в requirements, contracts, architecture і validation.

## 1. Що приймаємо як нові вимоги

- Підтримка фотографій, графіків, схем, таблиць і додаткових медіаматеріалів, включно з коректним використанням матеріалів інших дослідників.
- Профіль авторського стилю, який контролює користувач.
- Постійний, конфігурований каталог ресурсів із різними призначеннями.
- Режими створення нового документа та роботи з наявним.
- Явні ролі планування, пошуку, наукового аналізу, написання та критики.
- Збережений реєстр аналогів; 3–5 пріоритетних систем для глибокого дослідження і прямого повторного використання придатних компонентів.
- Reuse-first: не переписувати з нуля те, що можна прийнятно використати, адаптувати чи форкнути.

Користувач не завершив речення про розміщення папки статті/дисертації. Тому `projects/<slug>/` нижче — пропонований default, а не погоджене місце зберігання.

## 2. Візуальні матеріали — частина доказової бази

Не ставимо квоту «мінімум N картинок». Кожна ілюстрація повинна мати роль: показати результат, пояснити метод, порівняти роботи чи документувати спостереження. Рольова схема не потребує окремого постійного агента-дизайнера: asset tools і процедура підготовки figure достатні для початку.

| Вид | Що зберігати | Перевірка |
|---|---|---|
| Власний графік із results | Result row IDs, data hash, код побудови, параметри, файл | Дані, осі, unit, legend, interval/aggregation, повторна генерація |
| Власне фото/відео спостереження | Оригінал, автор/походження, дата за наявності, transformations | Не змінено зміст спостереження; контекст і згода, якщо застосовні |
| Власна концептуальна схема | Редагований source, твердження/метод, caption | Відповідність тексту; схема не подається як вимірювання |
| Чужа figure без змін | DOI/URL, paper version, page/figure number, license/permission basis | Атрибуція, умови повторного використання, відповідність контексту |
| Адаптована чужа figure | Те саме + список змін | Caption вказує адаптацію; права на модифікацію перевірено |
| Новий графік за чужими даними | Джерело даних, процедура extraction, unit, uncertainty | Розрізняти raw dataset, таблицю і приблизну digitization |
| Synthetic illustrative image | Generator/prompt, purpose, label | Ніколи не видавати за спостереження чи результат експерименту |

Графіки результатів будуються кодом із даних. Генератор зображень може створювати лише доречні концептуальні ілюстрації; не домальовує вимірювання чи експериментальні зразки.

Посилання на статтю саме по собі не встановлює дозволу на відтворення її figure. Перевіряємо права конкретного матеріалу, включно з credit line: навіть у відкритій статті можуть бути сторонні ілюстрації з іншими умовами. Наприклад, CC BY 4.0 дозволяє копіювання та адаптацію за умов атрибуції, посилання на ліцензію й позначення змін. Можливість іншої підстави, як-от законний виняток, залежить від обставин; harness не визначає її автоматично. Перемалювання зображення не повинно вважатися способом автоматично обійти умови використання.

Asset record: `id`, `kind`, `purpose`, `origin`, `source_id`, `source_version`, `source_locator`, `original_hash`, `derived_hash`, `data_refs`, `generator_or_script`, `transformations`, `caption`, `alt_text`, `rights_basis`, `rights_evidence`, `rights_status`, `review_status`. Непотрібні поля — null із причиною.

`rights_status`: unresolved / documented / incompatible. Для draft допустимий placeholder із unresolved; перед фінальним export використовувані сторонні assets повинні мати задокументовану придатну підставу. Це технічна перевірка записів, не юридична сертифікація.

## 3. Авторський стиль: керована редакторська функція

Підтримуємо впізнаваний голос автора. Ціль формулюємо як «зберегти авторський стиль і його контроль над текстом», а не як гарантію, що сторонній читач вважатиме текст написаним без AI.

Вхід: 2–3 зразки власних текстів або явні вподобання. Не визначати науковий стиль лише за короткими повідомленнями в чаті. Враховувати мову, жанр і різницю між одноосібною та співавторською роботою.

Author profile: formal/informal register, first-person preference, sentence/paragraph tendencies, terminology, transition preferences, рівень деталізації, приклади бажаного/небажаного формулювання, заборонені кліше. Користувач редагує профіль; система показує короткий тестовий абзац для калібрування. Не виводити особистісні чи психологічні характеристики з тексту.

Пріоритети: точність і межі доказів → вимоги видання → погоджений стиль. Стилізація не має перетворювати «може свідчити» на «доводить», видаляти limitations або змінювати числа. Не копіювати фактичні твердження зі style samples у нову статтю. AI-disclosure обробляється окремо за правилами видання/установи і ліцензіями використаних компонентів; стиль не є механізмом приховування походження.

## 4. Каталог ресурсів: призначення, доступ і пріоритет

Система пам'ятає політику пошуку у файлі конфігурації, а не покладається на довільну пам'ять LLM. Каталог — стартовий набір, не замкнений whitelist. Конкретна тема може потребувати галузевих індексів, конференцій чи репозиторіїв даних.

| Ресурс | URL | Роль у harness |
|---|---|---|
| Google Scholar | https://scholar.google.com/ | Пошук публікацій, цитувань, версій; інтерактивний/manual fallback за потреби |
| Semantic Scholar | https://www.semanticscholar.org/ | Пошук статей, references/citations, metadata; офіційний API adapter |
| Clarivate Master Journal List | https://mjl.clarivate.com/ | Перевірка журналу, колекції/індексування; не заміна пошуку змісту статей |
| Scopus Sources | https://www.scopus.com/sources | Перевірка source title і coverage; окремо від article search у Scopus |
| ResearchGate | https://www.researchgate.net/ | Виявлення роботи/авторської копії; зіставлення з первинною версією |
| Crossref | https://www.crossref.org/documentation/retrieve-metadata/rest-api/ | DOI, metadata, publication updates; metadata не підтверджують claim |
| OpenAlex | https://help.openalex.org/ | Додатковий індекс дослідницьких робіт і зв'язків; API |
| arXiv | https://info.arxiv.org/help/api/index.html | IT/AI препринти й версії; publication/review status записується окремо |
| Видавець / офіційні proceedings / repository | Залежить від роботи | Повний текст, первинні дані, додатки, код; пріоритет для перевірки evidence |

Registry fields: `resource_id`, `url`, `purpose`, `topic_scope`, `access_method`, `credentials_required`, `available`, `priority`, `usage_constraints`, `last_checked`, `fallback`. Не зберігати API keys у самому registry.

Не кожна сесія мусить опитувати всі ресурси. Search plan визначає покриття, запити та критерії завершення; query log фіксує також невдалий доступ. Якщо ресурс недоступний, report відрізняє «не перевірено» від «нічого не знайдено». Не обходити CAPTCHA чи доступ; використовувати доступні API, дозволені exports або матеріали користувача.

Індексування журналу, citation count і наявність DOI — різні metadata signals. Жоден із них не робить окреме твердження автоматично істинним. Для venue verification зберігати назву, ISSN, конкретну колекцію, coverage years і дату перевірки; статус не узагальнювати на всі роки.

## 5. Нова робота та редагування

`operation_mode`: create / revise / extend / respond_to_reviewers. Окремо: `document_kind`: article / thesis / report. Тип документа не визначає режим роботи.

Якщо користувач дав manuscript або завдання «виправ Results», система пропонує revise і показує виявлений scope. Уточнення потрібне лише коли файл/версія/ціль справді неоднозначні. Не ставити однакові вступні питання щоразу.

Для revise: original snapshot → import report → погоджений scope → change plan → section diffs → affected claims/figures checks → integration review. Не перебудовувати весь manuscript заради локальної правки. Для respond_to_reviewers: таблиця comment → action → location → evidence → response; незгода з reviewer допустима з аргументами.

На старті: поточна версія, мета редагування, locked sections, доступні sources/results, target venue, style profile. Якщо немає повної інформації — зробити доступний analysis і показати gaps.

## 6. Ролі: що залишити, що змінити

Ролі описують відповідальність. Окремий agent session потрібен, коли є користь від свіжого контексту, паралельної незалежної задачі або обмеження прав. Роль не зобов'язана бути окремим процесом.

| Роль | Відповідальність | Output | Межа |
|---|---|---|---|
| Orchestrator | Intake, режим, dependencies, budget, gates, routing | brief/status/task assignments | Не вирішує наукову істинність |
| Planner | План дослідження, outline, dependencies, exit criteria | research plan + writing outline | На старті skill основного агента; не обов'язково окремий session |
| Researcher | Пошук і читання джерел, evidence, counterevidence | source/excerpt records, search log | Не підміняє джерело summary без provenance |
| Scientific analyst / methodologist | Дизайн, аналіз, припущення, валідність висновків | protocol, result interpretation, claim assessments | Не «джерело істини»; не затверджує безпомилковість власної роботи |
| Scientific writer/editor | Пише частини за section brief і voice profile | section draft + claim refs + diff | Не створює нові дані чи сильніші висновки |
| Critic/reviewer | Піддає сумніву evidence/аргументацію, перевіряє цілісність | findings + severity + evidence + revision task | Не приймає claim голосуванням і не перезаписує raw data |

Головне виправлення: «науковець визначає істину» замінюємо на «науковий аналітик визначає, що підтримують доступні докази і які є обмеження». Джерелом перевірки є первинні матеріали, дані, протокол і відтворювані обчислення. Вони теж можуть містити помилки, тому їх походження і якість треба оцінювати. Людина приймає рішення про інтерпретацію/публікацію, але її approval також не створює наукової істини.

Scientific analyst визначає допустиму силу висновків; stylistic tone визначають author profile і writer. Не викликати analyst на кожне форматування: тригери — нова гіпотеза, метод, metric, result, material claim, limitation або зміна conclusion.

Пропозиція MVP: один основний session для orchestration/planning/research/writing; окремі контексти для складного analysis і критики за потреби. Це до трьох типів execution context, а не шість постійних агентів. Під час pilot порівняти з окремими шістьма ролями за тієї самої моделі й бюджету, якщо є підстава очікувати користь.

Розбіжність analyst/critic → конкретний disputed claim + докази обох сторін → додаткова перевірка/експеримент → unresolved або рішення автора з rationale. Не нескінченний debate. Два цикли revision — початковий configurable limit; потім report blockers.

## 7. Писати частинами, перевіряти ціле

Section brief: goal, central question, allowed claims, evidence refs, figure refs, dependencies on other sections, terminology, scope/length, style_profile_version, exit criteria.

Основний цикл: section brief → evidence/analysis → draft → section review → revision. Після завершення ключових розділів обов'язковий integration pass: abstract/contributions/results/conclusions, терміни, позначення, citation keys, нумерація figures, відсутність дублювання й суперечностей. Висновки не додають результатів, яких немає в основному тексті.

Паралельні section drafts не пишуть один файл одночасно: окремі outputs, один integrator. Передавати короткі structured handoffs і refs на файли, не всі transcript усіх агентів.

## 8. Папка і нові артефакти

Пропонований root: `projects/<stable-id>-<slug>/`. Для дисертації — `thesis/` зі study references, без копіювання всіх джерел кожного розділу.

До структури v0.1 додаємо:

- `intake.json`: operation/document/study kinds, scope і resolved inputs.
- `profiles/author-style.md`: стиль, provenance зразків, версія, user edits.
- `config/source-policy.yaml`: ресурсний каталог і access capabilities.
- `manuscript/original/`, `manuscript/sections/`, `manuscript/diffs/`: редагування зі збереженням авторського тексту.
- `assets/original/`, `assets/derived/`, `assets/manifest.json`: походження ілюстрацій, зміни, captions і права.
- `analysis/plot-scripts/`: відтворювані графіки.
- `reviews/integration.md`, `reviews/response-to-reviewers.md`.

Це логічна структура. Для малої статті не створювати порожні папки й надмірну кількість службових файлів.

## 9. Реєстр п'яти пріоритетних аналогів

Використовуємо вже досліджені commit snapshots від 2026-10-13, щоб не змішувати висновки між версіями. 2026-10-20 повторно завантажено LICENSE саме цих commits. Це не перевірка всіх нових commits після 13 жовтня і не повний аудит transitive dependencies.

| Пріоритет | Репозиторій | Що розглядати для reuse | Root license на зрізі |
|---|---|---|---|
| 1 | [open-paper-machine](https://github.com/TobiasBlask/open-paper-machine) | Workflow/skills, section verification, audit prompts; кандидат на основу/fork | MIT |
| 2 | [PaperQA](https://github.com/Future-House/paper-qa) | Retrieval, evidence contexts, citation keys, source metadata | Apache-2.0 |
| 3 | [AutoResearchClaw](https://github.com/aiming-lab/AutoResearchClaw) | Stage contracts, checkpoint/budget patterns, придатні tools і тести | MIT |
| 4 | [OpenDraft](https://github.com/MorMar7/opendraft-paperwriter) | Section pipeline, citation workflow, structured uncertain outcomes | MIT |
| 5 | [AI-Scientist-v2](https://github.com/SakanaAI/AI-Scientist-v2) | Experiment journal, runs, ablations; розширення після writing MVP | The AI Scientist Source Code License |

Known weak validators з попереднього аудиту не копіюємо як гарантії: AutoResearchClaw numerical membership і OpenDraft topical relevance потребують іншого контракту/виправлення.

### Перевірені license links і revisions

- `TobiasBlask/open-paper-machine` — `160df4d13d266411f0850c4de7ecdbd93e8b40be`; [LICENSE](https://raw.githubusercontent.com/TobiasBlask/open-paper-machine/160df4d13d266411f0850c4de7ecdbd93e8b40be/LICENSE).

- `Future-House/paper-qa` — `57e89f7223b0960d5ee5ea048c69e3c47e088572`; [LICENSE](https://raw.githubusercontent.com/Future-House/paper-qa/57e89f7223b0960d5ee5ea048c69e3c47e088572/LICENSE).

- `aiming-lab/AutoResearchClaw` — `be4ba4755bf1b52220f25e13b2293b5956590070`; [LICENSE](https://raw.githubusercontent.com/aiming-lab/AutoResearchClaw/be4ba4755bf1b52220f25e13b2293b5956590070/LICENSE).

- `MorMar7/opendraft-paperwriter` — `89128b30d9857cf9b871cbebc88ec07832260b9a`; [LICENSE](https://raw.githubusercontent.com/MorMar7/opendraft-paperwriter/89128b30d9857cf9b871cbebc88ec07832260b9a/LICENSE).

- `SakanaAI/AI-Scientist-v2` — `96bd51617cfdbb494a9fc283af00fe090edfae48`; [LICENSE](https://raw.githubusercontent.com/SakanaAI/AI-Scientist-v2/96bd51617cfdbb494a9fc283af00fe090edfae48/LICENSE).

MIT дозволяє широке повторне використання за збереження copyright/license notice. Apache-2.0 має власні умови redistribution, notices і змін. Перевірити конкретні файли, bundled assets, prompts та dependencies: root license не обов'язково покриває сторонні включення.

У прочитаній ліцензії AI-Scientist-v2 п. 3.2.e вимагає явного помітного повідомлення про машинне походження/використання AI Scientist у наукових manuscripts, papers і technical reports; п. 3.3 стосується передачі обмежень далі. Це суттєва відмінність від MIT/Apache; компонент не можна просто позначити нашою MIT-ліцензією. Для MVP доцільно почати з перших чотирьох, а п'ятий використовувати як дослідницький reference до рішення про adoption.

### Інші вже знайдені репозиторії — зберігаємо в backlog

- [AgentLaboratory](https://github.com/SamuelSchmidgall/AgentLaboratory), включно з AgentRxiv.
- [AI-Scientist v1](https://github.com/SakanaAI/AI-Scientist).
- [HKUDS AI-Researcher](https://github.com/HKUDS/AI-Researcher).
- [OpenScholar](https://github.com/AkariAsai/OpenScholar).
- [STORM](https://github.com/stanford-oval/storm).
- [AutoScholarLoop](https://github.com/damonwan1/AutoScholarLoop).

Ці шість не видаляються з реєстру; глибокий adoption-аудит обмежуємо п'ятьма пріоритетними. Закриті Elicit, Kosmos і Google co-scientist залишаються функціональними references, не джерелом недоступного internal code.

## 10. Політика повторного використання

Погоджуємо принцип «поліпшувати наявне». Не погоджуємо автоматичне «забрати все»: так переносимо несумісні assumptions, dependencies і дефекти. Одиниця рішення — компонент разом із його контрактом, ліцензією і тестом користі.

Для кожного кандидата: repo+SHA → конкретні paths → input/output → call path → prompt/schema → validators → failure/resume → dependencies → license/NOTICE → fixture run → рішення `use_dependency / vendor / fork / adapt / reject`.

Переваги варіантів:

- Dependency: менше власної підтримки; прийнятні API/dependencies, version pinning.
- Vendor: невеликий самодостатній модуль/промпт; зберегти upstream path/SHA/license і патчі.
- Fork: більша частина workflow підходить; можна підтримувати upstream sync і не переписувати ядро.
- Independent implementation: лише коли reuse несумісний із вимогами або умовами; письмово пояснити причину.

Для кожного скопійованого компонента потрібен adoption record: origin URL/SHA/path, destination path, license, notices, changes, acceptance test, update policy. Якщо адаптуємо текст промпту, походження також зберігаємо. Проєкт матиме `THIRD_PARTY_NOTICES.md` і `third_party/manifest.json`, коли з'явиться фактичний запозичений код.

Перший практичний spike: open-paper-machine як base/fork проти thin composition його процедур із PaperQA-compatible evidence contracts. Один і той самий реальний manuscript/fixture; порівняти потрібні зміни, provenance, resume, revision safety і підтримку host. Не вибирати основу лише за stars чи довжиною README. Не перетягувати новий runtime заради одного невеликого prompt.

Зараз збережено shortlist, license check і план adoption. Новий глибокий аудит п'яти повних систем, їх запуск та копіювання модулів ще не виконані; ця зміна бачення не видається за готову реалізацію.

## 11. Доповнення до вимог і тестів

| ID | Нова вимога | Acceptance scenario |
|---|---|---|
| FR-17 | Figure/asset registry із походженням, data refs, captions і rights | T17: без source/rights evidence стороння figure не проходить final export |
| FR-18 | Відтворювані власні plots | T18: зміна input data інвалідує plot і залежні claims; повторна побудова |
| FR-19 | Versioned author profile, керований користувачем | T19: style rewrite зберігає numbers, citations, qualifiers і limitations |
| FR-20 | Resource policy з purpose/access/fallback | T20: недоступний ресурс позначається unavailable, coverage gap не приховується |
| FR-21 | Create/revise/extend/respond_to_reviewers | T21: локальна правка не змінює locked sections; збережено original/diff |
| FR-22 | Section briefs та integration review | T22: суперечність abstract↔results виявлена після окремо прийнятих sections |
| FR-23 | Role outputs, bounded disagreements і людське рішення | T23: конфлікт analyst/critic не перетворюється на auto-PASS або endless loop |
| FR-24 | Реєстр reuse, license/provenance і component acceptance | T24: кожен adopted file має origin/notice/test; невідомі права не замовчуються |
| FR-25 | Обробка figures із чужих даних/цифрування | T25: приблизна digitization явно позначена; не видається за original raw data |

ASR additions: assets входять у dependency graph; author profile окремий від scientific assessments; source policy окрема від source evidence; revise вимагає diff-preserving edits; adopted components ізольовані від canonical domain contracts.

## 12. Рішення, які варто обговорити

1. Чи згодні замінити роль «джерела істини» на scientific analyst, який оцінює підтримку тверджень і методологію?
2. Чи приймаємо шість логічних ролей із кількома execution contexts замість шести постійних агентів?
3. Чи open-paper-machine має бути першим кандидатом на fork/base, чи пріоритет — однакова робота в обох hosts відразу?
4. Яке місце для папок статей/дисертацій ти мав на увазі в незавершеному пункті?

Ці питання не блокують подальший read-only аналіз кандидатів. Рішення про нові зовнішні інтеграції/витрати приймається за конкретним сценарієм.

## 13. Джерела для уточнень

Перевірено 2026-10-20:

- [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/): дозволи, attribution і позначення змін; конкретну figure ліцензію перевіряємо окремо.
- [GitHub: Licensing a repository](https://docs.github.com/articles/licensing-a-repository): публічний доступ до repository сам по собі не дає загального права reuse без відповідної ліцензії.
- [Google Scholar Help](https://scholar.google.com/intl/en/scholar/help.html): пошук, references/cited by, full-text versions.
- [Clarivate Master Journal List](https://mjl.clarivate.com/): призначення каталогу журналів.
- [Scopus content](https://www.elsevier.com/products/scopus/content): coverage/source lists.
- [Semantic Scholar API](https://api.semanticscholar.org/api-docs/): пошук і publication graph.
- [ResearchGate Help](https://help.researchgate.net/getting-started): обмін і виявлення дослідницьких робіт.
- Crossref, OpenAlex та arXiv official docs наведені у ресурсному каталозі вище.

Попередній аудит і його зафіксовані snapshots використані як вихідна база. Цей документ не стверджує, що API access уже налаштований або що весь код кандидатів виконувався.
