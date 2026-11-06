# Decisions and corrections log (chronological)

Read this to avoid repeating mistakes.

1. Task page read via a summarising fetch tool; wording is paraphrased -> re-read the real page on the day.
2. **Claude wrongly said 11 am was the submission deadline.** Page: files are *sent* at 11 am. User: files + key arrive 11:00, **submission deadline 15:00**. Schedule rebuilt for 4 hours.
3. API docs page is JS-rendered (empty on fetch). Chrome extension not connected. Used `openapi.json` instead (saved in repo). Never viewed the docs page itself. If Chrome connects later, compare page vs spec.
4. **Claude wrongly estimated per-flat fetching at ~11 min.** Correct: ~110 min per endpoint at 10 req/s. Decision: fetch by suburb in bulk.
5. Discovery: suburb endpoint `listings/rent-history` (date range, paged) and `properties` -> bulk strategy. It returns post-cutoff adverts unless `to_date` set (spec example dated 2026-10-28).
6. **Claude wrongly said the spec had no response schemas.** It has schemas/examples; field names recorded in api.md.
7. User chose: whole folder pushed to a new **public** GitHub repo `microburbs-rent-task` (remote `mine`); `origin` (Microburbs org) left untouched.
8. Fetcher built with rate limiting, SQLite cache, paging, leakage guard; 19 mocked tests pass; CLI smoke-tested with stubbed HTTP. Not yet tested on the real API.
9. **Tuning rule tightened:** earlier advice "don't overtune on the holdout" was too soft; the rule is no tuning on the check pile at all.
10. Model choice: LightGBM on log rent with L1/Huber objective; baseline first; optional XGBoost/seed ensemble. SHAP for insights.
11. **SHAP units correction:** contributions are in log units if trained on log rent (percentage-like), not dollars.
12. Heat map (OpenStreetMap + filters + median/mean) wanted for the presentation; decided it cannot fit before 15:00 -> parallel teammate or after submission.
13. Wiki + PLAN.md + CLAUDE.md update requested so nothing is forgotten; created in `rents/wiki/`.
14. Not done yet (planned next): baseline model, CSV validator, report generator, heat-map scaffold on fake data, library installs, commit/push of the latest files.
