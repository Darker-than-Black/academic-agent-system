# Архітектура і рішення

## ADR-001: використовувати наявний агентний runtime

Пропозиція: запускати research workflow у Codex або Claude Code. Harness не реалізує власний цикл модель→tools і не потребує API-ключа для ще одного LLM-сервісу. Агент читає інструкції й викликає локальний CLI. Runtime-specific адаптер містить тільки точки входу та посилання на спільні правила.

Перевага: маленька поверхня підтримки. Обмеження: бюджет/permissions основного агента контролює host; harness не може гарантувати обмеження довільних команд, виконаних поза його CLI. Перевірки експорту захищають якість його власного output bundle, а не блокують усі можливі дії користувача.

## ADR-002: один writer, файли замість сервера

Python CLI `rh` + Markdown/JSON/JSONL на диску. JSON Schema Draft 2020-12; code-level cross-reference validators. Мінімальні залежності: CLI parser стандартної бібліотеки, jsonschema; PDF/BibTeX parsers — окремі адаптери з зафіксованими версіями. Конкретні версії обирає implementer після перевірки сумісності, не вигадує зі спеки.

У MVP один процес змінює study. Lock з run ID; при аварії lock відновлюється явною recovery процедурою. Writes: staging directory → validation → atomic rename snapshot → atomic update current pointer. Незавершені staging файли не є completed state. JSONL event log діагностичний, snapshots авторитетні; обірваний хвіст журналу ізолюється, не приховується.

## ADR-003: provenance спочатку, RAG за потреби

Source registry і точні excerpts з locator; пошук по локальних матеріалах починається з індексу metadata та текстового пошуку. Embeddings/vector DB не потрібні до доведеної проблеми пошуку. Наявність джерела в registry не означає підтримку claim. Повнотекстовий доступ і OCR-quality зберігаються явно.

## ADR-004: перевірки двох типів

Детерміновані: schema, links, hashes, cite keys, arithmetic, tuple matching, missing outputs, stale dependencies, policy gate. Семантичні: чи випливає claim з excerpt, чи коректне узагальнення, чи достатній baseline. Семантичне рішення — reviewer assessment із підставами й невизначеністю; його не називаємо доказом наукової істини.

Числовий renderer підставляє власні результати з result rows. Нові числа після редактури повторно звіряються. Для арифметичних похідних потрібні expression, input row IDs, script hash та precision policy.

## ADR-005: bounded workflow з необов'язковим review

Стадії мають явні входи/виходи й exit conditions, але основний агент може обирати наступну корисну дію. До двох повторів при тимчасовому tool failure; semantic revision максимум два цикли за замовчуванням, потім report unresolved. Ці числа — робочі defaults, не наукові норми.

Reviewer працює у свіжому контексті; може читати evidence і формувати findings, але не переписувати raw results або сам схвалювати G3. Додавання reviewer — предмет A/B тесту. Сам факт іншої ролі чи моделі не гарантує незалежність.

## ADR-006: експорт двох класів

`draft`: дозволяє прогалини, містить помітний статус і unresolved report.
`verified`: означає лише, що зазначені технічні перевірки виконані для даного snapshot, critical claims розглянуті людиною й G3 записаний. Не означає peer review, прийняття журналом або доведену істинність. У UI краще показувати «Перевірено за профілем X», а не «Науково валідно».

Hard blockers: broken evidence links, contradictory material claim без виправлення, missing result provenance для власного результату, simulated result поданий як real, stale required checks, unresolved protocol deviation, absent G3. Source без DOI не blocker сам по собі. Не всі зауваження reviewer є blockers; їхня класифікація і resolution записані.

## Межі компонентів

- Runtime adapter: інструкції, виклик CLI, індикація можливостей host.
- Core: state transitions, artifact registry, dependencies, gate evaluation.
- Tools: джерела, metadata lookup, parser, results import, optional execution, export.
- Validators: структурна/числова перевірка; semantic assessments — вхідні артефакти.
- Project data: raw sources/results, protocol, draft, claims, findings, approvals.

MCP у майбутньому може експонувати ті самі tools. Це спосіб виклику, а не архітектура наукового процесу. Спершу забезпечити роботу CLI на одному runtime; переносимість перевірити на іншому без дублювання правил.
