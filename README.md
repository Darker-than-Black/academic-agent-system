# Research Harness

`rh` — це CLI (інтерфейс командного рядка), не залежний від конкретного
середовища, який допомагає одному авторові готувати наукові статті та
дисертації так, щоб їхні твердження, числа й висновки були простежувані до
доказів. Критичні до правильності перевірки виконує саме CLI, а не підказки
агента чи хуки (ADR-001 rev.2).

Спілкування з автором веде агент-хост (наразі Claude Code, Codex — з M3).
Автор звертається до агента (зазвичай українською), агент викликає `rh` і
передає результати.

## Структура репозиторію

- `harness/` — пакет `research-harness` (команди `rh` і `rh-dev`), схеми,
  конфігурації, правила, тести.
- `Projects/` — робочий простір автора (статті та дисертації). На нього
  **не поширюється** ліцензія harness — див. [`PROJECTS_NOTICE.md`](PROJECTS_NOTICE.md).
- `research-harness-spec/spec-v0.2/` — специфікація реалізації (також
  віддзеркалена в Project docs).

## Встановлення

Потрібен [`uv`](https://docs.astral.sh/uv/). Далі:

```
cd harness
uv sync
```

Версію Python закріплено у `harness/.python-version` і `harness/pyproject.toml`
(потрібен Python ≥ 3.12).

## Запуск

```
cd harness
uv run rh version          # версія harness (JSON-конверт)
uv run rh-dev check        # перевірки репозиторію (ruff, format, pytest, заборонені шляхи)
uv run rh-dev lint         # лише ruff check + ruff format --check (швидко, без pytest)
uv run rh-dev install-hooks  # увімкнути git-хук pre-commit (запускає rh-dev lint)
```

Хук `pre-commit` лежить у `harness/scripts/git-hooks/` і відстежується в git.
Після `install-hooks` кожен коміт запускає `rh-dev lint`, щоб помилки E501 та
форматування ловилися до коміту, а не пізніше у `rh-dev check`. Пропустити
разово: `git commit --no-verify`.

`rh` — єдиний компонент, якому дозволено змінювати стан об'єктів. `rh-dev` —
окрема точка входу для перевірок репозиторію та генерації фікстур; кінцевим
користувачам вона не потрібна.

## Ліцензія

Harness поширюється під ліцензією Apache-2.0 (див. [`LICENSE`](LICENSE) і
[`NOTICE`](NOTICE)). Сторонні файли зберігають власні ліцензії — див.
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
