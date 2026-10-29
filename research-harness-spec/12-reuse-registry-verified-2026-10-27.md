# Реєстр повторного використання — перевірка на рівні файлів

Дата: 2026-10-27. Статус: результат перевірки; рішення «копіювати/адаптувати» — пропозиції до обговорення. Доповнює `02-landscape-audit.md` і §9–10 `11-vision-addendum-2026-10-20.md`.

## Як перевіряли

П'ять репозиторіїв клоновано з GitHub; для кожного звірено зафіксований у спеці SHA з головною гілкою, існування кожного шляху на обох ревізіях і SHA-256 вмісту з `evidence/source-manifest.json`; переглянуто дерево файлів, frontmatter skills, LICENSE/NOTICE, заголовки модулів, імпорти та ключові символи. Код не запускався; промпти й модулі прочитані вибірково (заголовки, сигнатури, релевантні фрагменти), не построково. Юридичного висновку тут немає — це технічна перевірка записів.

## 1. Стан зафіксованих комітів

| Репозиторій | Pinned SHA | Дата коміту | Головна гілка зараз | Нових комітів після pin |
|---|---|---|---|---|
| TobiasBlask/open-paper-machine | 160df4d | 2026-04-10 | main = 160df4d (v6.4.0) | 0 |
| Future-House/paper-qa | 57e89f7 | 2026-08-12 | main = c692d0d (2026-10-25) | 2 |
| aiming-lab/AutoResearchClaw | be4ba47 | 2026-08-19 | main = be4ba47 | 0 |
| MorMar7/opendraft-paperwriter | 89128b3 | 2026-09-10 | master = 89128b3 | 0 |
| SakanaAI/AI-Scientist-v2 | 96bd516 | 2025-12-19 | main = 96bd516 | 0 |

**Перевірено:** усі 17 шляхів зі спеки існують і на pinned SHA, і на головній гілці; жоден не переміщено. SHA-256 усіх 17 файлів на pinned SHA збігається з `source-manifest.json`. У paper-qa два нові коміти змінили `agents/tools.py` (1 рядок) і `clients/retractions.py` (3 рядки) — лише type-ignore коментарі, поведінка не змінилась; `prompts.py` не змінено.

## 2. Головний реєстр

Рішення: **копіювати** — переносимо файл майже без змін; **адаптувати** — беремо файл як основу і переписуємо під наш контракт; **лише ідея** — файл не копіюємо; **відхилити** — не використовувати навіть як шаблон.

| # | Фіча | Репозиторій | Шлях (функції / розділи) | Статус перевірки | Ліцензія | Рішення | Причина |
|---|---|---|---|---|---|---|---|
| 1 | Головний агент, фази 0–8, checkpoints, журнал оркестрації | open-paper-machine | `agents/paper-machine.md` (Orchestration Log, RS1–RS8, PHASE 0–8, EXECUTION RULES) | Існує, hash ✓ | MIT | Адаптувати | Найближчий аналог нашого workflow; посилається на відсутній скрипт (див. §5) і не має CLI-валідації |
| 2 | Перевірка цитувань: 3 рівні доступу, рубрика, пріоритизація | open-paper-machine | `skills/verification-engine/SKILL.md` (Step 1–5; рубрика VERIFIED / PLAUSIBLE / MISMATCH / UNVERIFIABLE / NOT FOUND; Tier A/B/C; Tier 1–3 prioritization) | Існує, hash ✓ | MIT | Адаптувати | PLAUSIBLE = збіг теми без явного підтвердження; у нас це `partial`/`insufficient`, а не `supported` |
| 3 | Аудит «стаття ↔ код» | open-paper-machine | `skills/audit-engine/SKILL.md` (Step 1–5; CONFIRMED / PARTIAL / MISSING / MISMATCH / NOT_AUDITABLE; звіт з file:line) | Існує, hash ✓ | MIT | Копіювати + доповнити | Хороша процедура; додати зв'язок із result rows і execution provenance |
| 4 | Пошук літератури, snowballing | open-paper-machine | `skills/literature-engine/SKILL.md` + MCP `academic-search-mcp` (зовнішній PyPI пакет) | Skill існує; MCP-пакет не перевірено | MIT (skill); пакет — не перевірено | Адаптувати | Skill посилається на неіснуючий `scripts/academic_search.py` |
| 5 | Обробка рецензій, change plan, revision log | open-paper-machine | `skills/review-engine/SKILL.md`, `commands/respond-reviewers.md` | Існує | MIT | Адаптувати | Пряма відповідь на `respond_to_reviewers` (FR-21) |
| 6 | Симуляція peer review | open-paper-machine | `skills/peer-review-engine/SKILL.md`, `commands/review-paper.md` | Існує | MIT | Адаптувати | Основа для ролі critic; LLM-review лишається advisory |
| 7 | Оцінка ідеї до написання (Pursue / Refine / Kill) | open-paper-machine | `skills/idea-engine/SKILL.md`, `agents/idea-critic.md`, `agents/research-strategist.md`, `agents/brainstormer.md` | Існує | MIT; README вказує натхнення research-companion (Andre Huang, MIT) | Адаптувати | Gate перед протоколом; перевірити, чи є там текст із research-companion |
| 8 | Тексти розділів (шаблони абзаців) | open-paper-machine | `skills/writing-engine/SKILL.md`, `commands/draft-section.md` | Існує | MIT | Адаптувати | Узгодити з section brief, author profile і claim ledger |
| 9 | Методологія, теорія, позиціонування | open-paper-machine | `skills/method-engine`, `theory-engine`, `positioning-engine` (SKILL.md) | Існує | MIT | Адаптувати | Planner / analyst; method-engine — 797 рядків, потрібне скорочення |
| 10 | Systematic review / PRISMA screening | open-paper-machine | `skills/screening-engine/SKILL.md`, `commands/screen-papers.md` | Існує | MIT | Лише ідея (LATER) | FR-15 поза MVP |
| 11 | CRediT, розподіл людина/AI | open-paper-machine | `skills/coauthor-engine/SKILL.md` | Існує | MIT | Адаптувати | Корисно для AI-disclosure і співавторства в дисертації |
| 12 | Підготовка до подачі, LaTeX, слайди | open-paper-machine | `skills/submission-engine`, `latex-engine`, `presentation-engine` | Існує | MIT | Лише ідея (LATER) | Після MVP |
| 13 | Ілюстрації через PaperBanana | open-paper-machine | `skills/figure-engine/SKILL.md`, `scripts/paperbanana_direct.py` | Існує | MIT; пакет `paperbanana` (Gemini) — не перевірено | Лише ідея | Генерує зображення AI; для результатних графіків потрібен код із даних (addendum §2) |
| 14 | Наукові skills K-Dense (citation-management, statistical-analysis, scientific-critical-thinking, peer-review, scientific-writing тощо) | open-paper-machine (вендорено з K-Dense-AI/claude-scientific-skills) | `scientific-skills/*/SKILL.md` | Існує; автор у frontmatter | Різні: MIT (K-Dense, 21 skill; AHK Strategies, 2), Apache-2.0 (markdown-mermaid-writing), BSD-3 (networkx, seaborn, statsmodels), matplotlib license | Копіювати вибірково | Брати з першоджерела K-Dense, а не з копії; ліцензію вказувати по кожному skill |
| 15 | Промпти «спершу докази», відмова за браком даних, cite keys | paper-qa | `src/paperqa/prompts.py` (`summary_prompt`, `summary_json_prompt`, `qa_prompt`, `answer_iteration_prompt_template`, `citation_prompt`) | Існує, hash ✓, без змін | Apache-2.0 | Адаптувати | Текст промптів — у нашу бібліотеку інструкцій із NOTICE і позначкою змін |
| 16 | Інструменти пошуку / збору доказів / відповіді | paper-qa | `src/paperqa/agents/tools.py` (`EnvironmentState`, `PaperSearch`, `GatherEvidence`, `GenerateAnswer`, `Reset`, `Complete`) | Існує, hash ✓ | Apache-2.0 | Лише ідея (або dependency) | Залежить від fhaviary, lmi, litellm, tantivy — власного LLM-runtime, що суперечить ADR-001 |
| 17 | Перевірка відкликаних статей | paper-qa | `src/paperqa/clients/retractions.py` (`RetractionDataPostProcessor`) | Існує, hash ✓, косметичні зміни | Apache-2.0 | Адаптувати | 92 рядки; дані з api.labs.crossref.org (Retraction Watch). Умови використання даних — не перевірено |
| 18 | Оцінка журналу | paper-qa | `src/paperqa/clients/journal_quality.py` + `client_data/journal_quality.csv` | Існує | Код Apache-2.0; CSV — походження не перевірено | Не копіювати CSV | Невідоме джерело даних; у нас venue verification через MJL/Scopus |
| 19 | Контракти етапів (входи, виходи, DoD, error code, retries) | AutoResearchClaw | `researchclaw/pipeline/contracts.py` (`StageContract`, `CONTRACTS` для 23 етапів) + `stages.py` (enum `Stage`) | Існує, hash ✓ | MIT | Адаптувати | Структура — майже наш контракт; етапи замінити на наші |
| 20 | Атомарні checkpoints і resume | AutoResearchClaw | `researchclaw/pipeline/runner.py` (`_write_checkpoint` — temp + rename, `_write_heartbeat`, `read_checkpoint`, `resume_from_checkpoint`) | Існує, hash ✓ | MIT | Адаптувати | Патерн для ADR-002; runner має 1864 рядки, тому беремо функції, не файл |
| 21 | SHA-256 маніфест артефактів | AutoResearchClaw | `researchclaw/hitl/checksums.py` (119 рядків, stdlib) | Існує | MIT | Копіювати + адаптувати | Без сторонніх залежностей; основа для dependency hashes |
| 22 | Бюджетні пороги (50/80/100%) | AutoResearchClaw | `researchclaw/hitl/cost_guard.py` (132 рядки, stdlib) | Існує | MIT | Адаптувати | FR-13 / NFR-05; додати стан unknown, коли telemetry немає |
| 23 | Diff між версіями артефактів | AutoResearchClaw | `researchclaw/hitl/diff_view.py` (151 рядок, difflib) | Існує | MIT | Адаптувати | Режим revise, FR-08 / FR-21 |
| 24 | Перевірка назв умов і конфігу тренування в тексті | AutoResearchClaw | `researchclaw/pipeline/paper_verifier.py` (`_check_condition_names`, `_check_training_config`) | Існує, hash ✓ | MIT | Лише ідея | Залежить від `verified_registry.py` (див. #25) |
| 25 | Реєстр «перевірених» чисел | AutoResearchClaw | `researchclaw/pipeline/verified_registry.py` (`add_value`, `_add_variants` ×100/÷100, `is_verified` з допуском 1%) | Існує | MIT | Відхилити | Перевіряє належність числа до множини значень без tuple (metric, split, condition) — той самий клас дефекту, що й #26 |
| 26 | Числова та фактична перевірка claims | AutoResearchClaw | `researchclaw/hitl/claim_verifier.py` (`_verify_numerical`, `_verify_factual`) | Існує, hash ✓ | MIT | Відхилити | Відтворений false positive (95 секунд ≈ 95% accuracy); word overlap ≠ entailment |
| 27 | Промпти етапів і бюджетного масштабування | AutoResearchClaw | `prompts.default.yaml` | Існує, hash ✓ | MIT | Лише ідея | Скорочення seeds заради часу у нас — protocol deviation |
| 28 | Фазовий генератор чернетки, preconditions, retry | OpenDraft | `engine/draft_generator.py`, `engine/phases/{research,structure,citations,compose,validate,compile}.py` | Існує, hash ✓ | MIT | Лише ідея | Прив'язано до Gemini й платних API |
| 29 | Checkpoint/resume після кожної фази | OpenDraft | `engine/utils/checkpoint.py` (237 рядків) | Існує | MIT | Лише ідея | Дублює #20; вибрати один патерн |
| 30 | Розділення «джерело існує» і «змістова оцінка», UNCERTAIN | OpenDraft | `engine/utils/citation_claim_verifier.py` (`ClaimCitationPair`, `CitationClaimVerdict`, `CitationClaimVerifier`) | Існує, hash ✓ | MIT | Адаптувати структури, не judge | Judge оцінює topical relevance; ліміт 25 пар; текст обрізається до 25k + 25k символів — неповне покриття |
| 31 | Перевірка DOI через Crossref, URL status | OpenDraft | `engine/utils/citation_validator.py` (486 рядків) | Існує | MIT | Адаптувати | Шар existence/metadata_status; timeout → `lookup_failed`, не `not_found` |
| 32 | Дедуплікація джерел (DOI / URL / назва / автор+рік) | OpenDraft | `engine/utils/deduplicate_citations.py` (384 рядки) | Існує | MIT | Адаптувати | Не зливати preprint і публікацію — пов'язувати |
| 33 | Схема бази цитувань | OpenDraft | `engine/utils/citation_database.py` (645 рядків) | Існує | MIT | Лише ідея | У нас власні Source/Excerpt schemas |
| 34 | Критик / рецензент | OpenDraft | `engine/prompts/04_validate/skeptic.md`, `referee.md`, `factcheck_extract.md`, `factcheck_judge.md` | Існує | MIT | Адаптувати | Роль critic; judge переписати під support verdict |
| 35 | Голос автора (persona matching) | OpenDraft | `engine/prompts/05_refine/voice.md` | Існує | MIT | Лише ідея | Основа для author profile (FR-19); профіль редагує користувач |
| 36 | «Anti-AI-detection» стилізація | OpenDraft | `engine/prompts/05_refine/entropy.md` | Існує | MIT | Відхилити | Прямо ставить ціль приховати AI-походження — суперечить addendum §3 і академічній доброчесності |
| 37 | Журнал експериментів, дерево спроб, ablations | AI-Scientist-v2 | `ai_scientist/treesearch/journal.py`, `agent_manager.py`, `parallel_agent.py` | Існує, hash ✓ (2 з 3 у manifest) | The AI Scientist Source Code License | Лише ідея | Ліцензія п. 3.2.e.i вимагає помітного disclosure у кожному manuscript; п. 3.3 — передавати обмеження далі |
| 38 | LLM / VLM рецензія (включно з figures) | AI-Scientist-v2 | `ai_scientist/perform_llm_review.py`, `perform_vlm_review.py` | Існує | Та сама | Лише ідея | Та сама причина; ідея VLM-перевірки figure корисна для FR-17 |

## 3. Повний перелік можливостей за репозиторієм

### open-paper-machine (v6.4.0)

Склад: 4 агенти, 17 engines, 21 команда, 24 вендорені наукові skills, plugin manifest для Claude Code з MCP `academic-search`.

| Етап нашого циклу | Компоненти | Корисність |
|---|---|---|
| Intake / оцінка ідеї | idea-engine; агенти idea-critic, research-strategist, brainstormer; команди `/evaluate-idea`, `/brainstorm`, `/triage-project`, `/scooping-check` | Висока |
| Discovery | literature-engine; `/search-papers`, `/monitor-literature`; screening-engine, `/screen-papers` | Висока / LATER для SLR |
| Protocol | method-engine, theory-engine | Середня |
| Analysis | qualitative-engine, `/analyze-interviews`; scientific-skills statistical-analysis, statsmodels, exploratory-data-analysis | Середня (залежить від кейсу) |
| Argument | positioning-engine, `/analyze-positioning` | Середня |
| Draft | writing-engine, `/draft-section`, `/write-paper`, `/analyze-writing` | Висока |
| Figures | figure-engine, `/generate-figure`, `/generate-plot`; scientific-skills matplotlib, seaborn, plotly, scientific-visualization, scientific-schematics | Середня |
| Review | verification-engine, `/verify-citations`; audit-engine, `/audit-paper`; peer-review-engine, `/review-paper` | Висока |
| Revise | review-engine, `/respond-reviewers` | Висока |
| Package | latex-engine, `/export-latex`; submission-engine, `/prepare-submission`; presentation-engine, `/generate-slides`; coauthor-engine | LATER, крім coauthor |
| Не для нас | research-grants, consciousness-council, what-if-oracle, pyzotero, networkx | Низька / за потребою |

### paper-qa

Agent tools (PaperSearch, GatherEvidence, GenerateAnswer, Reset, Complete, ClinicalTrialsSearch); metadata clients (Crossref, OpenAlex, Semantic Scholar, Unpaywall); journal quality і retractions postprocessors; локальний індекс (tantivy); PDF readers окремими пакетами; конфіги якості/швидкості. Для нас корисні: промпти, модель EnvironmentState як ідея, retraction lookup, metadata clients як референс.

### AutoResearchClaw

23-етапний pipeline зі StageContract; checkpoints / heartbeat / resume; HITL-модулі (checksums, cost_guard, diff_view, escalation, smart_pause, intervention); debate і tournament; requirements_judge; власні skills у `.claude/skills/`; external agents (без ліцензійних файлів, ColliderAgent не вендорено). Корисні: contracts, checkpoints, checksums, cost_guard, diff_view. Escalation через Slack/email — поза нашим scope.

### OpenDraft

Шість груп промптів (research → structure → compose → validate → refine → enhance); фази; утиліти цитувань (validator, dedup, database, claim verifier, API clients до Crossref / OpenAlex / Semantic Scholar та платних сервісів); quality_gate; output_validators; checkpoint; revise. Позиціонується, зокрема, для thesis drafts — корисний референс для життєвого циклу дисертації.

### AI-Scientist-v2

BFTS-дерево експериментів, journal, stage manager, LLM/VLM review, writeup, plotting. Лише як референс через ліцензію.

## 4. Ліцензії на рівні файлів

| Репозиторій | Root | Інші ліцензії всередині | Що з цього випливає |
|---|---|---|---|
| open-paper-machine | MIT (© 2025 Tobias-Benedikt Blask) | `scientific-skills/`: MIT (K-Dense Inc., 21; AHK Strategies, 2), Apache-2.0 (Clayton Young / Superior Byte Works, 1), BSD-3 (networkx, seaborn, statsmodels), matplotlib license; README згадує research-companion (MIT) | Root MIT не покриває все; ліцензія і автор — по кожному skill. Окремого NOTICE-файлу немає |
| paper-qa | Apache-2.0 | `packages/paper-qa-pymupdf/LICENSE` — **AGPL-3.0**; інші пакети Apache-2.0; `journal_quality.csv` — походження не встановлено | Не підключати й не копіювати pymupdf-reader; CSV не брати |
| AutoResearchClaw | MIT (© 2026 Aiming Lab) | `external/agents/*` без LICENSE-файлів | Не копіювати з `external/` |
| OpenDraft | MIT (© 2025 SCAILE Technologies GmbH) | Окремих ліцензій не знайдено; залежності від платних API | Копіювати можна; залежності не тягнути |
| AI-Scientist-v2 | The AI Scientist Source Code License v1.0 (на базі Responsible AI License v1.1) | — | П. 3.2.e.i: помітний disclosure про машинну генерацію у кожному manuscript; п. 3.3: обмеження обов'язкові в будь-якій угоді щодо похідних робіт |

Транзитивні залежності (pyproject / requirements) повністю не аудитовано.

## 5. Знайдені дефекти та розбіжності

1. **open-paper-machine:** `skills/literature-engine/SKILL.md` (рядки 6, 25) і `agents/paper-machine.md` (рядок 201) посилаються на `scripts/academic_search.py`, якого немає в репозиторії; пошук перенесено в MCP-пакет `academic-search-mcp`. При копіюванні ці інструкції треба виправити.
2. **open-paper-machine:** статус PLAUSIBLE означає збіг теми без явного підтвердження. Якщо перенести рубрику без змін, relevance знову стане «майже supported» — те, що ми свідомо виправляємо (T06).
3. **AutoResearchClaw:** `verified_registry.py` генерує варіанти ×100 / ÷100 і перевіряє число з допуском 1% проти всієї множини значень. Це той самий membership-підхід, що й у відтвореному false positive, а не лише окрема функція.
4. **OpenDraft:** claim verifier обробляє максимум 25 пар і обрізає довгий текст — без явного coverage report результат не можна вважати повною перевіркою.
5. **OpenDraft:** `entropy.md` — промпт для обходу AI-детекторів.

## 6. Перевірене і неперевірене

**Перевірено в цьому проході:** існування pinned SHA; існування й hash 17 файлів зі спеки; відсутність переміщень на головних гілках; дерева файлів п'яти репозиторіїв; root LICENSE і вкладені LICENSE; frontmatter ліцензій усіх `scientific-skills`; сигнатури й docstrings модулів, вказаних у таблиці; диф paper-qa для трьох ключових файлів; конкретні фрагменти, наведені в §5.

**Не перевірено:** запуск будь-якого коду; повний текст промптів і skills (прочитано заголовки, рубрики, сигнатури); транзитивні залежності та їхні ліцензії; пакети `academic-search-mcp` і `paperbanana`; умови використання даних Retraction Watch через Crossref Labs; походження `journal_quality.csv`; чи містять agents open-paper-machine текст, запозичений із research-companion; повний вміст K-Dense skills (апстрім перевірено лише на рівні ліцензії, шляхів і розбіжності з копією — §7). Шість backlog-репозиторіїв (AgentLaboratory, AI-Scientist v1, AI-Researcher, OpenScholar, STORM, AutoScholarLoop) у цей прохід не входили.

## 7. Погоджені рішення (автор, 2026-10-27)

| Питання | Рішення автора | Рядки реєстру |
|---|---|---|
| open-paper-machine | Адаптувати engines: потрібні SKILL.md копіюються в наш repo і переписуються під наші статуси, CLI-перевірки та claim ledger. Fork усього плагіна — ні | #1–9, #11 |
| AutoResearchClaw | Переносимо всі чотири: `checksums.py`, checkpoint/resume (функції з `runner.py` + `StageContract`), `cost_guard.py`, `diff_view.py` | #19–23 |
| K-Dense scientific skills | Вибірково (орієнтовно 5–8), з першоджерела, ліцензія по кожному skill | #14 |
| Відхилення | Погоджено: `verified_registry.py`, `claim_verifier.py`, `entropy.md` не використовуємо; з AI-Scientist-v2 — лише ідеї. Числові валідатори пишемо власні, tuple-based | #25–26, #36–38 |

### Перевірка першоджерела K-Dense

`K-Dense-AI/claude-scientific-skills` @ `5f2bc0341354fd5590aef76a533ada1e1e5b4e62` (2026-10-26): root LICENSE — MIT (© 2025 K-Dense Inc.); у `skills/` 177 каталогів. Кандидати, усі з `license: MIT` у frontmatter, усі суттєво відрізняються від копій в open-paper-machine (апстрім оновлений):

| Skill | Шлях в апстрімі | Рядків |
|---|---|---|
| statistical-analysis | `skills/statistical-analysis/SKILL.md` | 453 |
| scientific-critical-thinking | `skills/scientific-critical-thinking/SKILL.md` | 235 |
| citation-management | `skills/citation-management/SKILL.md` | 359 |
| peer-review | `skills/peer-review/SKILL.md` | 317 |
| scientific-writing | `skills/scientific-writing/SKILL.md` | 381 |
| literature-review | `skills/literature-review/SKILL.md` | 229 |
| hypothesis-generation | `skills/hypothesis-generation/SKILL.md` | 290 |
| scientific-visualization | `skills/scientific-visualization/SKILL.md` | 307 |

Остаточний вибір 5–8 skills робимо після опису життєвого циклу: беремо лише ті, що закривають конкретний етап. Вміст skills (крім frontmatter) у цьому проході не читався.

## 8. Наступні кроки

1. Для кожного рядка «Копіювати / Адаптувати» перед перенесенням: adoption record (origin URL / SHA / path → destination, ліцензія, зміни, acceptance test) — `third_party/manifest.json` і `THIRD_PARTY_NOTICES.md`.
2. Після опису життєвого циклу (етап 0, п. 2.5) зіставити кожен етап із рядками реєстру й остаточно обрати K-Dense skills.
3. Додати в базу оцінювання негативні кейси з §5 (relevance ≠ support, ×100-варіанти, coverage < 100%).
