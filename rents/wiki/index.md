# Rent task wiki – START HERE

Memory of everything decided and learned while preparing for the Microburbs hackathon **rent task** (competition day: **Sat 7 Nov 2026**). Written the night before. Claude: read this index first, then the pages relevant to what you are doing. When something changes, update the page AND add a line to `decisions-and-corrections.md`.

## Pages
| Page | What it holds |
| --- | --- |
| [task-rules.md](task-rules.md) | The task as published: deliverables, scoring, constraints, the cutoff rule, plain-English reading of each sentence |
| [schedule.md](schedule.md) | Competition-day timeline (files arrive 11:00, submit by 15:00), freeze/submit rules, tonight's prep, fallbacks |
| [api.md](api.md) | Microburbs API: auth, limits, envelope, endpoints that matter, response shapes, gotchas |
| [fetching.md](fetching.md) | Bulk-fetch strategy, `rents/fetcher.py` usage, caching, leakage guard, time maths |
| [data-and-geography.md](data-and-geography.md) | Input files, suburbs (29 vs 33), G-NAF ids, ABS mesh blocks, joins, the 4,246 missing addresses |
| [modelling.md](modelling.md) | Recommended model (LightGBM), why, features, car-space handling, ensemble, improvement order |
| [validation-and-split.md](validation-and-split.md) | Date split, tuning rules, metrics (median abs error, within $100, R squared), retrain ambiguity |
| [explainability-shap.md](explainability-shap.md) | SHAP / feature importance, what to show in the report, caveats |
| [report-and-heatmap.md](report-and-heatmap.md) | `report.html` contents, heat map design (OpenStreetMap + filters), honesty labelling |
| [repo-and-environment.md](repo-and-environment.md) | Repo layout, remotes, public-repo cautions, Python env, Windows gotchas, git state |
| [decisions-and-corrections.md](decisions-and-corrections.md) | Chronological log of decisions and mistakes corrected (read this to avoid repeating them) |
| [open-questions.md](open-questions.md) | Things still unknown; ask organisers / check on the day |
| [glossary.md](glossary.md) | Terms: G-NAF, mesh block, SAL, SHAP, R squared, etc. |

## The ten things not to get wrong
1. **Nothing dated after 31 Jul 2026** may be used to build, tune or check. Never use `listings/for-rent`. The API itself returns post-cutoff adverts unless you send `to_date=2026-07-31`.
2. **Never tune on the check pile** (the later adverts up to 31 Jul). Tune inside the earlier adverts only.
3. **Timeline:** files + key arrive **11:00**; submission deadline **15:00**. Freeze modelling at 14:15, submit by 14:45.
4. **A valid safety CSV first** (baseline by ~12:15), then improve. Empty answers score worse than wrong ones.
5. CSV must have **exactly 65,777 unique `gnaf_id`s**, no extras, no blanks, columns `gnaf_id, rent_with_car_space, rent_without_car_space`; keep with ≥ without.
6. **Fetch by suburb (bulk), not per flat.** Per-flat = ~110 min per endpoint at 10 req/s.
7. **Private files** (past leases, census blocks) must never be committed or republished. The GitHub repo is PUBLIC. Put them only in `rents/data/` (gitignored).
8. **Never commit or print the API key.** It lives in `.env` (`MICROBURBS_API_KEY`).
9. `report.html` must **lead with insights**, then held-out score, R squared, the date-split explanation, data and method.
10. **Ask the organisers** the open questions (submission channel, retrain-on-check-pile) as early as possible.
