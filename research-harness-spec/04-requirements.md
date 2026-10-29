# Вимоги та простежуваність

MUST — умова приймання MVP. SHOULD — бажана властивість, відхилення записується. LATER — поза MVP.

## Functional requirements (FR)

| ID | Вимога | Перевірка |
|---|---|---|
| FR-01 | MUST init із питання й матеріалів; невідомі значення зберігаються явно | T01 |
| FR-02 | MUST import джерел з ідентичністю, версією, доступністю та provenance; DOI необов'язковий | T02 |
| FR-03 | MUST зберігати питання/запит, provider, дату, результати пошуку та причини включення/відхилення | T02 |
| FR-04 | MUST versioned protocol і рішення G1/G2 | T03 |
| FR-05 | MUST відрізняти imported, executed, simulated, failed runs; simulated не підтверджує реальний результат | T04 |
| FR-06 | MUST зв'язувати власні числові claims із result row: run, dataset, split, metric, unit, aggregation | T05 |
| FR-07 | MUST claim ledger з locator, support verdict, coverage і criticality | T06 |
| FR-08 | MUST генерувати/редагувати Markdown + BibTeX, зберігати авторські зміни через preview diff | T07 |
| FR-09 | MUST review report: помилки, unknown, stale, not-applicable, покриття; жодного порожнього PASS | T08 |
| FR-10 | MUST виявляти змінені dependencies й інвалідувати залежні перевірки | T09 |
| FR-11 | MUST resume з останнього завершеного checkpoint, без повторного запуску побічних дій | T10 |
| FR-12 | MUST draft/verified export із manifest; verified потребує G3 й відсутності blockers | T11 |
| FR-13 | MUST журнал tool errors, timeouts, витрат і зупинка при вичерпанні бюджету | T12 |
| FR-14 | SHOULD опційний reviewer у свіжому сеансі з draft+evidence; без повноважень схвалення | T13 |
| FR-15 | LATER thesis composition та institution profiles, systematic review profile | майбутні fixtures |
| FR-16 | MUST за замовчуванням не публікувати й не надсилати матеріали; доступ до зовнішніх сервісів у межах явної конфігурації | T14 |

## Non-functional requirements (NFR)

| ID | Сценарій й критерій приймання |
|---|---|
| NFR-01 Integrity | Переривання запису не лишає успішний checkpoint із відсутнім output; перевірити fault injection (T10) |
| NFR-02 Portability | Один project directory переноситься на іншу машину; усі внутрішні refs відносні; без приватної БД (T11) |
| NFR-03 Explainability | Кожен blocker має ID, location, причину, evidence refs та запропоновану дію (T08) |
| NFR-04 Performance | Локальна структурна перевірка fixture: 100 sources / 200 claims / 20 runs, p95 <5 с на задокументованій машині; без мережі/LLM (T15). Ціль, ще не виміряна |
| NFR-05 Cost control | Перед LLM/compute дією перевіряється бюджет; якщо runtime не дає token/cost telemetry, unknown не стає zero. Підтримати ліміт часу/дій (T12) |
| NFR-06 Privacy | Ключі й секрети не потрапляють у bundle/logs; секрет із fixture маскується; недовірений PDF не змінює permissions (T14) |
| NFR-07 Maintainability | Детерміновані validators не залежать від LLM SDK; ядро не імпортує runtime adapter (T15) |
| NFR-08 Reproducibility | Run містить code/data/config/environment fingerprints або явний missing; результат без цього не позначається locally_reproduced (T04) |
| NFR-09 Usability | Дослідник бачить наступну дію, blockers і невідоме в одному status report; pilot міряє час і кількість уточнень (T16) |

## Architecturally significant requirements (ASR)

ASR — не окремий список фіч, а вимоги з істотними наслідками для архітектури.

| ID | Вихідні вимоги | Наслідок |
|---|---|---|
| ASR-01 | FR-06/07/10, NFR-08 | Typed provenance і dependency hashes; текст не є єдиним станом |
| ASR-02 | FR-11, NFR-01 | Atomic snapshots, single writer, idempotency keys |
| ASR-03 | NFR-07, FR-14 | Runtime-neutral CLI; prompt adapter окремо від validators |
| ASR-04 | FR-09/12, NFR-03 | Перевірка стану експорту в коді; prompt/hook не є гарантією |
| ASR-05 | FR-13/16, NFR-05/06 | Межі інструментів, бюджет, explicit external actions |

Вимоги не обіцяють перевірити кожну приховану помилку. Coverage має явний знаменник: усі зареєстровані material claims плюс результат сканування рукопису на незареєстровані твердження. LLM-сканер може пропускати claims; це окремий об'єкт вимірювання.
