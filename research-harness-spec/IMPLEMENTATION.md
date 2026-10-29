# Інструкція для реалізації у Codex або Claude Code

Це завдання на розробку, а не автоматично активна skill або host configuration.

Прочитай README, requirements, architecture, contracts і validation. Реалізуй етапи 1–3 roadmap послідовними маленькими змінами. Почни з runtime-neutral ядра та fixtures; не створюй власний LLM orchestrator, web UI, vector DB, MCP server чи багато агентів без нової обґрунтованої вимоги.

Запропонована структура майбутнього репозиторію: `src/research_harness/{cli,state,artifacts,validation,adapters,export}/`, `schemas/`, `instructions/`, `templates/`, `tests/{unit,integration,fixtures}/`, `docs/adr/`. Не створюй модулі лише для заповнення структури.

1. Уточни наявний repository context та локальні правила. Підготуй pyproject і lockfile. Обери підтримувану версію Python та зафіксуй її.
2. Доповни schemas для всіх сутностей із 06-contracts. Реалізуй валідатори cross refs, dependencies і invalidation. Приклади не є production даними.
3. Реалізуй atomic state, single writer, operation IDs і recovery. Додай fault-injection tests.
4. Додай import local sources/results, claim ledger і structural/numeric validation. Спочатку offline fixtures, потім network adapters.
5. Додай спільні інструкції агенту та один host adapter. Перевір актуальну офіційну документацію host, не вигадуй синтаксис commands/hooks. Уся correctness-critical перевірка виконується CLI також без hook.
6. Додай exports, gate records і coverage report. Не дозволяй `unknown` автоматично проходити required check. Не зберігай secrets. Не запускай сторонні дослідницькі репозиторії без контрольованого execution plan.
7. Виконай mandatory tests і надай report: що працює, що не реалізовано, фактичні commands, evidence й обмеження. Проведи A/B pilot, коли користувач надасть real case та бюджет.

Зберігай hand-edited manuscript; пропонуй diff. Не генеруй фіктивних бібліографічних записів, approvals чи експериментів для проходження тесту. Не називай simulated runs реальними. Якщо є методологічне питання — продовжуй незалежну технічну роботу і винеси конкретне рішення автору.

Не копіюй сторонній код/промпти без окремої перевірки ліцензії й attribution. Поточна спека використовує власні формулювання й узагальнені патерни.
