# Адаптер Claude Code (v0)

Цей адаптер дає змогу працювати з Research Harness через Claude Code: почати
об'єкт, пройти анкету в розмові, побачити статус, продовжити — із забороною на
`holdout/` та приватні шляхи й позначенням агентських оболонок.

## Що встановлено

- `AGENTS.md` (корінь репозиторію) — інструкції для агента (англійською, бо це
  машинний шар; H15). `CLAUDE.md` лише імпортує `AGENTS.md`.
- `.claude/settings.json` (корінь) — забороняє читати й шукати `**/holdout/**`,
  `.env`, `*.local.yaml`; задає `RH_AGENT_SESSION=1` і `RH_HOST=claude-code` для
  оболонок, якими користується агент.
- `harness/host/claude-code/commands/{start,continue,status,intake}.md` — тонкі
  команди-обгортки навколо `rh`. Щоб увімкнути їх як слеш-команди проєкту,
  скопіюйте ці файли у `.claude/commands/` (назва файлу = назва команди).

## Де запускати `rh gate record`

**У своєму власному вікні термінала, не в оболонці агента.**

Причина: `.claude/settings.json` задає `RH_AGENT_SESSION=1` для оболонок агента,
а `rh gate record` відмовляється записувати рішення, коли ця змінна встановлена
(і коли stdin/stdout не є справжнім терміналом). Навіть якщо команди, які ви
запускаєте власноруч у режимі оболонки Claude Code, успадкують `RH_AGENT_SESSION`
або не матимуть TTY, запис схвалення не відбудеться — це навмисний запобіжник
(H14). Тому відкрийте окремий термінал, перейдіть у каталог `harness/` і
виконайте показану агентом команду, наприклад:

```
cd harness
uv run rh --object A-2026-001 gate record G0
```

`rh` покаже бриф, спитає рішення, причину (для відмови чи умов) і код
підтвердження, а потім запише схвалення. Після цього поверніться до агента й
скажіть «continue».

> Перевірка синтаксису хоста (H12): формати `.claude/settings.json`
> (`permissions.deny`, `env`) і слеш-команд (`.claude/commands/*.md` з
> frontmatter `description`, `argument-hint`, `$ARGUMENTS`) звірено з офіційною
> документацією Claude Code на дату реалізації — див. опис PR із URL і датами.

## v1: ролі, субагенти, навички (M2-13)

Дослідницький цикл і чернетку можна виконувати повністю в Claude Code:
оркестратор у головній сесії, а виконавці й рецензенти — субагенти зі свіжим
контекстом на своїх тирах.

- **Субагенти** (`agents/*.md`) **генеруються**, не пишуться вручну:
  ```
  cd harness
  uv run rh-dev host generate claude-code
  ```
  Джерела — `config/roles.yaml` (роль → тир), `config/model-tiers.yaml`
  (хост → тир → модель) і `harness/prompts/*.md` (системні підказки ролей).
  Ідентифікатор моделі кожного субагента береться з конфігурації — ніколи не
  вписується вручну. Кожен субагент (виконавець чи рецензент) отримує
  `disallowedTools: [Agent]`; делегувати може лише оркестратор головної сесії.
- **Пониження (downgrade, T63).** Якщо тир ролі відображається на `unknown`
  (напр. флагманська модель недоступна), субагента **не згенеровано** — генератор
  повідомляє проблему, а оркестратор має зупинитися або записати
  `rh model downgrade` після згоди автора (H7: `unknown` не проходить мовчки).
- **Навички** (`skills/<name>/SKILL.md`): `researcher`, `writer`, `critic`,
  `summarizer` — кожна лише вказує на команди `rh` і ніколи не стверджує статус,
  якого CLI не повернув.
- **Слеш-команди** (`commands/*.md`): `start`, `continue`, `status`, `intake`,
  `research`, `draft`, `review`, `export`.

Щоб увімкнути субагентів і навички для проєкту, скопіюйте `agents/` у
`.claude/agents/`, `skills/` у `.claude/skills/`, а `commands/` у
`.claude/commands/`.

> Перевірка синтаксису хоста (H12): формати субагентів
> (`.claude/agents/*.md`: frontmatter `name`, `description`, `tools`, `model`,
> `disallowedTools`) і навичок (`.claude/skills/<name>/SKILL.md`: `name`,
> `description`, `allowed-tools`) звірено з офіційною документацією
> (https://code.claude.com/docs/en/sub-agents,
> https://code.claude.com/docs/en/skills,
> https://code.claude.com/docs/en/slash-commands; дата: 2026-10-30).
