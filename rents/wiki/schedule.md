# Competition-day schedule (Sat 7 Nov 2026)

Fixed by the user: **files + API key arrive 11:00; submit by 15:00 (4 hours).**
(Also saved as the short `rents/docs/PLAN.md`.)

## Timeline
| Time | What | Done when |
| --- | --- | --- |
| 11:00-11:15 | Key into `.env` (`MICROBURBS_API_KEY`), start `python rents/fetcher.py adverts` then `properties`; copy private files into `rents/data/` | Fetch running |
| 11:15-11:45 | Inspect real data: advert fields, counts per suburb, date range, how many have price / car spaces; join flats to adverts (gnaf_id) and mesh blocks; count unmatched flats incl. the 4,246 | Join works, gaps known |
| 11:45-12:15 | Baseline: median rent by suburb x beds x baths with fallback chain; car-space premium; validator | **Valid safety CSV committed** |
| 12:15-13:45 | Real model: features, date split, LightGBM, one score on the check pile | Beats baseline |
| 13:45-14:15 | Error analysis, one improvement pass, optional 2nd model to average | **Final CSV frozen at 14:15** |
| 14:15-14:45 | `report.html` (insights, score, R squared, split, data+method); final validation of CSV | Report + CSV ready |
| 14:45-15:00 | Submit (buffer for slow upload / validator problems) | Submitted |

## Rules for the clock
- Freeze modelling at **14:15**. Late changes are how invalid files happen.
- Submit by **14:45** at the latest.
- If the model is not beating the baseline by **13:45**, submit baseline + whatever improvement works; spend the time on the report.
- Heat map does NOT fit before 15:00. A teammate builds it in parallel on fake data (only the final CSV needs dropping in); if working alone, build after submitting and plan the presentation accordingly (presentation time unknown: ask).

## Before the key arrives (morning / tonight)
1. Confirm `cd rents && python -m pytest -q` still passes (19 tests).
2. Have `.env` ready to receive the key (do NOT paste the key into chat or commit it).
3. Write the baseline model + CSV validator + report generator, tested on fake data (planned next, not yet written as of this wiki).
4. Scaffold the heat map with fake data (Leaflet + OpenStreetMap).
5. Agree roles if a team: (a) fetch + clean, (b) model, (c) report + heat map.
6. Install missing libs: pandas was MISSING; lightgbm / xgboost / shap not checked (see repo-and-environment.md).
7. Ask organisers: submission channel, retrain-on-check-pile allowed?, presentation time. (see open-questions.md)

## Fallback ladder (what to submit if things go wrong)
1. Final model CSV (validated).
2. Baseline CSV (suburb x beds x baths medians) committed at ~12:15.
3. Even simpler: suburb median for every flat (never blank).
Always run the validator on whatever is submitted.
