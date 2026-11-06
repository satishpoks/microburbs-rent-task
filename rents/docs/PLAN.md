# Plan for Sat 7 Nov 2026 (4 hours: files + key at 11:00, submit by 15:00)

Full detail: `rents/wiki/schedule.md`. Rules: `rents/wiki/task-rules.md`.

| Time | What | Done when |
| --- | --- | --- |
| 11:00-11:15 | Key into `.env`; run `python rents/fetcher.py adverts` then `properties`; private files into `rents/data/` | Fetch running |
| 11:15-11:45 | Inspect data; join flats to adverts + mesh blocks; count unmatched (incl. 4,246) | Joins work |
| 11:45-12:15 | Baseline (suburb x beds x baths medians), car-space premium, validator | Valid safety CSV committed |
| 12:15-13:45 | LightGBM (log rent, L1/Huber), date split, ONE check-pile score | Beats baseline |
| 13:45-14:15 | Error analysis, one improvement pass, optional 2nd model | CSV frozen 14:15 |
| 14:15-14:45 | `report.html` + final validation | Ready |
| 14:45-15:00 | Submit | Submitted |

Always: nothing after 31 Jul 2026; no tuning on the check pile; 65,777 unique ids, no blanks, with >= without; never commit the key or private files (repo is public).
Heat map (OpenStreetMap, filters, median/mean): parallel teammate on fake data, or after submission.
