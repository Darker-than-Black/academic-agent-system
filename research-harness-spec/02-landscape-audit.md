# Аудит аналогів: реалізації, промпти та рішення

Зріз 2026-10-13. Реєстр: 11 відкритих репозиторіїв, AgentRxiv як модуль AgentLaboratory, 3 системи за публічною документацією. «Усі» тут означає цей зафіксований набір, не весь ринок.

Це вибірковий code/prompt audit, не повний security audit і не benchmark. Наведені файли переглянуті в релевантних фрагментах/символах; згадка файла не означає прочитання кожного рядка. Commit links відтворюють досліджений зріз. Спостереження коду відділяються від нашої інтерпретації ризиків і рекомендацій.

Немає єдиного переможця: інструкційний harness, retrieval QA та автономна лабораторія вирішують різні задачі. Більшість корисних запозичень — contracts, evidence handling та bounded feedback, а не кількість агентів.

## 1. aiming-lab/AutoResearchClaw

**Реалізація.** Stage contracts описують inputs/outputs, DoD і retries; runner має файлові checkpoints. YAML містить окремі правила бюджету й наукового scope. Це Python workflow, не лише набір ролей.

**Промпти.** Є time-budget scaling і вимога не підміняти результати infrastructure logs. Корисна явність обмежень; скорочення seeds заради часу може змінити методологію — у нас це protocol deviation.

**Перевірка.** У `_verify_numerical` число шукається як підрядок у JSON експериментів. Ізольований запуск підтвердив false positive: training_seconds=95 підтримали claim 95% accuracy при справжньому test_accuracy=0.51. `_verify_factual` використовує word overlap. Це не entailment. Окремий `paper_verifier.py` має сильніші перевірки registry/conditions і допуски; локальний дефект не доводить, що весь pipeline пропустить приклад.

**Беремо:** contracts, checkpoints, явні budgets. **Не беремо:** global membership числа як підтвердження claim, confidence без калібрування. **Рішення:** незалежні tuple-based validators; T05/T08. Повний pipeline не запускався.

Код і промпти: [researchclaw/pipeline/runner.py](https://github.com/aiming-lab/AutoResearchClaw/blob/be4ba4755bf1b52220f25e13b2293b5956590070/researchclaw/pipeline/runner.py); [researchclaw/pipeline/contracts.py](https://github.com/aiming-lab/AutoResearchClaw/blob/be4ba4755bf1b52220f25e13b2293b5956590070/researchclaw/pipeline/contracts.py); [researchclaw/pipeline/paper_verifier.py](https://github.com/aiming-lab/AutoResearchClaw/blob/be4ba4755bf1b52220f25e13b2293b5956590070/researchclaw/pipeline/paper_verifier.py); [researchclaw/hitl/claim_verifier.py](https://github.com/aiming-lab/AutoResearchClaw/blob/be4ba4755bf1b52220f25e13b2293b5956590070/researchclaw/hitl/claim_verifier.py); [prompts.default.yaml](https://github.com/aiming-lab/AutoResearchClaw/blob/be4ba4755bf1b52220f25e13b2293b5956590070/prompts.default.yaml).

## 2. TobiasBlask/open-paper-machine

**Реалізація.** Інструкційний plugin: основний агент координує фази, checkpoints та журнал. Це найближчий аналог тонкого harness на готовому runtime. Логування і gates у прочитаних файлах задаються інструкціями; сам Markdown не забезпечує їх виконання.

**Промпти.** Idea evaluation перед drafting, критика contribution і рішення pursue/refine/kill. Verification engine працює з кожним місцем цитування, контекстом та різними рівнями доступу до джерела; відділяє явну підтримку від правдоподібності. Audit engine виділяє testable facts і звіряє з кодом.

**Обмеження.** Відповідність тексту репозиторію не доводить, що код запускався і дав заявлений результат. Вказаний у журналі варіант «No objection — auto-proceeded» не слід трактувати як явне наукове схвалення. Conclusion-first підхід варто застосовувати до важливості питання, а не до очікуваної перемоги методу.

**Беремо:** процедури, evidence tiers, citation occurrence audit, human checkpoints. **Додаємо:** enforced export checks, execution provenance, hash-bound approvals. **Рішення:** основний architectural reference; повна сумісність plugin не тестувалася.

Код і промпти: [agents/paper-machine.md](https://github.com/TobiasBlask/open-paper-machine/blob/160df4d13d266411f0850c4de7ecdbd93e8b40be/agents/paper-machine.md); [skills/verification-engine/SKILL.md](https://github.com/TobiasBlask/open-paper-machine/blob/160df4d13d266411f0850c4de7ecdbd93e8b40be/skills/verification-engine/SKILL.md); [skills/audit-engine/SKILL.md](https://github.com/TobiasBlask/open-paper-machine/blob/160df4d13d266411f0850c4de7ecdbd93e8b40be/skills/audit-engine/SKILL.md).

## 3. SamuelSchmidgall/AgentLaboratory

**Реалізація.** `LaboratoryWorkflow` веде literature review → planning → data preparation → experiments → interpretation → writing/refinement; має save_state, phase statistics і human-in-loop flags. Експериментальні code/output зберігаються як файли.

**Промпти.** `ReviewersAgent` робить три виклики з різними reviewer personas на тому самому model setting. Критика експериментів, impact і новизни розділена формулюваннями ролей. Це різні перспективи, але не гарантовано незалежні судження.

**AgentRxiv.** У тому самому файлі є клас із локальним сервером, пошуком завантажених papers, читанням PDF і модельним summary. Його розглянуто як розширення спільної пам'яті досліджень, не як окремий незалежно протестований продукт.

**Беремо:** фазові артефакти, phase cost/time, можливість людського втручання. **Не беремо в MVP:** professor/student topology і автоматичний обмін рукописами. Summary чужого AI-paper не прирівнюється до перевірених первинних даних. **Рішення:** workflow reference; експериментальні solvers та сервер не запускалися.

Код і промпти: [ai_lab_repo.py](https://github.com/SamuelSchmidgall/AgentLaboratory/blob/d9017d90e329112d2a80b7712f37ee9094d2cd27/ai_lab_repo.py); [agents.py](https://github.com/SamuelSchmidgall/AgentLaboratory/blob/d9017d90e329112d2a80b7712f37ee9094d2cd27/agents.py).

## 4. SakanaAI/AI-Scientist

**Реалізація.** Експериментальний цикл редагує template experiment.py, зберігає копію коду для run, запускає subprocess із timeout, читає final_info.json і передає результати наступній ітерації. Кількість runs і спроб обмежена.

**Промпти.** Coder спершу планує runs, отримує baseline і пише notes для майбутнього writeup. Reviewer має структурований JSON; у файлі є різні prompt variants, які по-різному трактують невпевненість. Наявність variant не доводить, що він default у всіх запусках.

**Обмеження.** Notes і aggregate means можуть втратити важливий контекст; копія коду не охоплює data/environment provenance. Модельний review score не є незалежною перевіркою експерименту.

**Беремо:** code snapshot per run, bounded execution, структурований review. **Додаємо:** raw outputs, split/config/environment hashes і negative-result reporting. **Не беремо:** загальну автономність як критерій якості. **Рішення:** корисний reference для optional runner, не база всього MVP.

Код і промпти: [ai_scientist/perform_experiments.py](https://github.com/SakanaAI/AI-Scientist/blob/1de1dbc1f4ee2c5f61e9c94348d55eb51d7fa2eb/ai_scientist/perform_experiments.py); [ai_scientist/perform_review.py](https://github.com/SakanaAI/AI-Scientist/blob/1de1dbc1f4ee2c5f61e9c94348d55eb51d7fa2eb/ai_scientist/perform_review.py).

## 5. SakanaAI/AI-Scientist-v2

**Реалізація.** Stage manager задає goals, iteration limits і structured progression/completion assessments. Tree-search agent розрізняє drafting, debug, improvement, tuning, seed nodes та ablations.

**Промпти.** Є окремі implementation/response guidelines і вимоги до збереження experiment data; експериментальні задачі отримують спеціалізовані інструкції щодо device, datasets, plotting. LLM reviewer запитує конкретні strengths/weaknesses та оцінки.

**Обмеження.** Schema `ready_for_next_stage` робить рішення структурованим, але не науково правильним. Tree search і численні candidate runs збільшують ресурсну вартість та ризик вибору лише вдалих результатів; це архітектурний ризик, не виміряний тут defect.

**Беремо:** явне розділення debug і наукового експерименту, журнал альтернатив, ablation/seed provenance. **Відкладаємо:** breadth-first experiment search до доведеної потреби. **Рішення:** advanced experiments reference; selected code paths прочитані, повний training/run не виконувався.

Код і промпти: [ai_scientist/treesearch/agent_manager.py](https://github.com/SakanaAI/AI-Scientist-v2/blob/96bd51617cfdbb494a9fc283af00fe090edfae48/ai_scientist/treesearch/agent_manager.py); [ai_scientist/treesearch/parallel_agent.py](https://github.com/SakanaAI/AI-Scientist-v2/blob/96bd51617cfdbb494a9fc283af00fe090edfae48/ai_scientist/treesearch/parallel_agent.py); [ai_scientist/perform_llm_review.py](https://github.com/SakanaAI/AI-Scientist-v2/blob/96bd51617cfdbb494a9fc283af00fe090edfae48/ai_scientist/perform_llm_review.py).

## 6. HKUDS/AI-Researcher

**Реалізація.** Main entry розділяє detailed idea, reference-based ideation і paper generation. Research path поєднує reference codebases, planning та додаткові експерименти; SectionComposer має checkpoints структури/підрозділів і злиття тексту.

**Промпти.** У plan path є вказівка додати експерименти для доведення переваги ідеї. Це конкретний ризик confirmation bias: наш prompt має перевіряти гіпотезу, включно з її спростуванням. У section fusion вимагається зберегти вміст підрозділів; це корисне обмеження втрат під час редагування, але не гарантія узгодженості.

**Беремо:** планування на основі матеріалів і checkpoints складного writeup. **Не беремо:** superiority-seeking критерій експериментів та випадковий вибір writing template як основу відтворюваної стилістики. **Додаємо:** versioned template і protocol deviations. **Рішення:** ideas reference, не dependency; container execution і повний workflow не тестувалися.

Код і промпти: [main_ai_researcher.py](https://github.com/HKUDS/AI-Researcher/blob/f9a6f8480860c193afff600eeffe3defcee8a978/main_ai_researcher.py); [research_agent/run_infer_plan.py](https://github.com/HKUDS/AI-Researcher/blob/f9a6f8480860c193afff600eeffe3defcee8a978/research_agent/run_infer_plan.py); [paper_agent/section_composer.py](https://github.com/HKUDS/AI-Researcher/blob/f9a6f8480860c193afff600eeffe3defcee8a978/paper_agent/section_composer.py).

## 7. MorMar7/opendraft-paperwriter

**Реалізація.** Фазовий draft generator перевіряє наявність research/structure/citation/compose outputs і підтримує retry wrapper. CitationClaimVerifier окремий від DOI existence checking.

**Промпти.** Найважливіша деталь: judge явно оцінює topical relevance за title/abstract, а не доведення конкретного claim. Extraction prompt обмежує вибірку максимум 25 claim-citation pairs. Отже, результат не можна називати повною верифікацією рукопису.

**Докази якості.** EVALUATION.md описує план оцінювання і історичний baseline до змін; це не виміряна поточна якість усіх модулів. Наявність багатьох тестових файлів не замінює запуску чи ручної оцінки claims.

**Беремо:** розділення metadata existence і змістового judgement, first-class uncertain, фазові preconditions. **Змінюємо:** support judgement замість relevance; coverage denominator і явний sampling. **Рішення:** citation subsystem reference. Усі провайдери й integration tests не запускалися.

Код і промпти: [engine/draft_generator.py](https://github.com/MorMar7/opendraft-paperwriter/blob/89128b30d9857cf9b871cbebc88ec07832260b9a/engine/draft_generator.py); [engine/utils/citation_claim_verifier.py](https://github.com/MorMar7/opendraft-paperwriter/blob/89128b30d9857cf9b871cbebc88ec07832260b9a/engine/utils/citation_claim_verifier.py); [EVALUATION.md](https://github.com/MorMar7/opendraft-paperwriter/blob/89128b30d9857cf9b871cbebc88ec07832260b9a/EVALUATION.md).

## 8. Future-House/paper-qa

**Реалізація.** Tools відокремлюють PaperSearch, GatherEvidence, GenerateAnswer, Reset і Complete; EnvironmentState зберігає документи, contexts і дії. Окремий metadata postprocessor працює з retraction data.

**Промпти.** Evidence summarization має збирати корисний матеріал, а не одразу відповідати; generation обмежує цитування доступними context keys та дозволяє відмовитися через недостатні дані. Ітерація не повинна переносити цитати, відсутні в новому context.

**Обмеження.** Summary може втратити qualifiers; relevance score не калібрована ймовірність підтримки. Метод Complete приймає success flag агента — це не незалежна наукова перевірка. Retraction lookup потребує актуальної доступної бази.

**Беремо:** evidence-before-answer, стабільні citation keys, abstention, source-status enrichment. **Додаємо:** exact excerpts і версії, audit coverage. **Рішення:** найкорисніший retrieval reference; можливість reuse визначити після dependency/license audit. Не прирівнюємо відкритий repo до всіх закритих можливостей PaperQA3/Edison.

Код і промпти: [src/paperqa/prompts.py](https://github.com/Future-House/paper-qa/blob/57e89f7223b0960d5ee5ea048c69e3c47e088572/src/paperqa/prompts.py); [src/paperqa/agents/tools.py](https://github.com/Future-House/paper-qa/blob/57e89f7223b0960d5ee5ea048c69e3c47e088572/src/paperqa/agents/tools.py); [src/paperqa/clients/retractions.py](https://github.com/Future-House/paper-qa/blob/57e89f7223b0960d5ee5ea048c69e3c47e088572/src/paperqa/clients/retractions.py).

## 9. AkariAsai/OpenScholar

**Реалізація.** Retrieval/reranking, generation, feedback, editing із додатковим retrieval та post-hoc attribution реалізовані окремими методами. Є параметри фільтрації/нормалізації за citation counts.

**Промпти.** Інструкції й few-shot приклади навчають знаходити недоліки відповіді, формулювати додаткові запити та виправляти текст із references. Це корисний цикл пошуку прогалин, а не загальна архітектура дисертації.

**Обмеження.** Post-hoc citations можуть підібрати близьку тему без достатньої підтримки первинного формулювання; потрібна перевірка exact claim. Citation-count preference може зміщувати вибір до популярних робіт; не використовувати як єдину quality metric. Це ризики підходу, не результати запуску цієї версії.

**Беремо:** targeted retrieval після виявлення прогалини, feedback з actionable question. **Не беремо:** автоматичне збереження початкового claim після підбору citation. **Рішення:** literature QA reference; важкі моделі/reranker не завантажувалися.

Код і промпти: [src/open_scholar.py](https://github.com/AkariAsai/OpenScholar/blob/0e9b8fb912273d3dae39e593da86e4f6d3bf8de1/src/open_scholar.py); [src/instructions.py](https://github.com/AkariAsai/OpenScholar/blob/0e9b8fb912273d3dae39e593da86e4f6d3bf8de1/src/instructions.py).

## 10. stanford-oval/storm

**Реалізація.** Engine розділяє knowledge curation, outline, article generation і polish та зберігає проміжні артефакти. Knowledge curation використовує perspective-guided розмову writer/expert, перетворює питання на queries і отримує evidence через retriever.

**Промпти.** DSPy signatures вимагають не повторювати питання, шукати інформацію за перспективою і будувати відповіді з доступних матеріалів; допускають відповідь про недостатність інформації.

**Обмеження.** Ціль цього прочитаного path — Wikipedia-подібна стаття. Це не перевірка наукової новизни, статистики чи execution provenance. Coverage кількох перспектив не означає систематичний огляд.

**Беремо:** outline після дослідження, пошук прогалин з кількох перспектив, розділення research і polish. **Не беремо:** simulated dialogue як обов'язкову топологію MVP. **Рішення:** useful writing/research pattern; collaborative STORM path і end-to-end quality не перевірялися.

Код і промпти: [knowledge_storm/storm_wiki/engine.py](https://github.com/stanford-oval/storm/blob/fb951af7744dab086e34962e9bc6fe878e145f83/knowledge_storm/storm_wiki/engine.py); [knowledge_storm/storm_wiki/modules/knowledge_curation.py](https://github.com/stanford-oval/storm/blob/fb951af7744dab086e34962e9bc6fe878e145f83/knowledge_storm/storm_wiki/modules/knowledge_curation.py).

## 11. damonwan1/AutoScholarLoop

**Реалізація.** Default pipeline будує ResearchGroupLoopPipeline з provider, literature, executor і LoopPolicy; execution backend за default dry-run. Прочитані ReviewStage і ReleaseStage записують structured artifacts.

**Промпти/контракти.** Review передає provider роль review_panel і schema hint. `_aggregate` об'єднує weaknesses/revisions; інші поля починає з першого review. Це не повноцінний консенсус ансамблю.

**Обмеження.** Прочитаний ReleaseStage пакує paths і reproducibility note без власної перевірки достовірності. Чи забезпечує потрібні gates повний nested loop, тут не встановлено: не робимо висновок про весь default pipeline з одного stage. Dry-run не слід подавати як empirical run.

**Беремо:** явні adapters і loop limits; **не переносимо:** success stage як scientific approval. LICENSE.md містить спеціальні умови й mandatory disclosure; не трактувати repo як безумовно permissive, ліцензійний review перед reuse окремий. **Рішення:** architecture reference лише; nested loop потребує глибшого аудиту перед adoption.

Код і промпти: [src/open_research_agent/core/pipeline.py](https://github.com/damonwan1/AutoScholarLoop/blob/8206c7581049a78cab9cf20723d70a846b43e7df/src/open_research_agent/core/pipeline.py); [src/open_research_agent/stages/review.py](https://github.com/damonwan1/AutoScholarLoop/blob/8206c7581049a78cab9cf20723d70a846b43e7df/src/open_research_agent/stages/review.py); [src/open_research_agent/stages/release.py](https://github.com/damonwan1/AutoScholarLoop/blob/8206c7581049a78cab9cf20723d70a846b43e7df/src/open_research_agent/stages/release.py); [LICENSE.md](https://github.com/damonwan1/AutoScholarLoop/blob/8206c7581049a78cab9cf20723d70a846b43e7df/LICENSE.md).

## 12. Elicit — публічний workflow/API

[API reference](https://docs.elicit.com/) розділяє report, systematicReview і agent sessions. Для review/report є явні executionStage, exportsStatus, quota pause/resume та unknown; agent session не обов'язково має той самий pipeline. [Опис systematic review](https://elicit.com/solutions/systematic-review) пов'язує extraction з джерелами.

**Беремо:** керовані screening/extraction поля, provenance, розділення job status і готовності exports. **Обмеження:** код, internal prompts і власне відтворення evaluation не доступні в цьому аудиті. Product claims не вважаємо незалежно підтвердженою якістю. Для нашого IT empirical MVP це джерело UX/контрактів, не обов'язкова платна dependency.

## 13. Kosmos — публічний опис архітектури

[How We Built Kosmos](https://advances.edisonscientific.com/research/how-we-built-kosmos/) описує перехід від довгого автономного запуску до persistent code-writing agent з world model і взаємодією з дослідником; окремо обговорює cloud execution та інструменти.

**Беремо:** довготривалу пам'ять як структуровані артефакти й можливість змінити напрям роботи. **Не переносимо в MVP:** хмарну платформу і складний world model без виміряної потреби. Наш file registry — обмежене практичне рішення, не еквівалент Kosmos. Internal prompts, deployment і cost/performance не перевірялися.

## 14. Google AI co-scientist — публічна дослідницька система

[Офіційний опис](https://research.google/blog/accelerating-scientific-breakthroughs-with-an-ai-co-scientist/) називає Generation, Reflection, Ranking, Evolution, Proximity та Meta-review і націлює систему на гіпотези/протоколи за метою науковця.

**Беремо:** порівняння альтернатив і критичний перегляд гіпотез. **Не переносимо:** tournament/coalition як необхідну архітектуру написання статті. Ранжування гіпотез не замінює їх експериментальної перевірки. Код і internal prompts у цьому аудиті не досліджені; не робимо твердження, що жодних відкритих реалізацій не існує.

## Підсумкова матриця перенесення ідей

| Ідея | Звідки | Рішення у нашій спеці |
|---|---|---|
| Тонкий workflow на host agent | open-paper-machine | ADR-001; спільні instructions |
| Evidence → answer, точні cite keys | PaperQA, OpenScholar | FR-02/07; Source/Excerpt/Claim |
| Context-aware citation audit | open-paper-machine, OpenDraft | FR-07/09; T06/T08 |
| Phase artifacts і resume | AgentLaboratory, AutoResearchClaw, STORM | ASR-02; T10 |
| Snapshot коду і bounded runs | AI-Scientist, v2 | FR-05/13; Run contract |
| Явна невизначеність API/job | Elicit, PaperQA | Tool envelope, unknown не PASS |
| Негативні приклади валідації | Probe AutoResearchClaw, аналіз OpenDraft | T05/T06; support ≠ relevance |
| Alternative hypotheses | Google co-scientist | Protocol, optional critique |
| Довготривала структурована пам'ять | Kosmos | File artifacts; без world-model engine |
| Не змішувати dry-run із результатом | AutoScholarLoop | execution_kind; T04 |

Не копіюємо role forests, publication scores, обов'язкову кількість references чи багатоступеневі loops без A/B користі. Ліцензії dependency/коду перевіряються перед запозиченням; посилання на архітектурну ідею не означає дозвіл скопіювати реалізацію.

## Що лишилося неперевіреним

Наскрізна поведінка всіх аналогів; default call paths усіх validators; regression suites; вартість; нові model versions; точність extraction із PDF/figures; закриті промпти; повна ліцензійна сумісність. Перед adoption компонента потрібен глибший аудит за roadmap. Для незалежного MVP достатньо зафіксованих вимог і негативних fixtures, але не можна називати цей документ завершеним аудитом кожного рядка аналогів.
