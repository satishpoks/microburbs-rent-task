# microburbs-hackathon-demos

Demo apps for the Microburbs hackathon API (`fastapi-property-report`, `nextjs-suburb-map`, `python-quickstart`, `streamlit-property-explorer`) plus the rent-prediction task in `rents/`.

## Rent task (hackathon day: Sat 7 Nov 2026; files + API key arrive 11:00, SUBMIT BY 15:00)
**Read `rents/wiki/index.md` first** (wiki-style memory of all discussion and decisions: task rules, schedule, API, fetching, data/geography, modelling, validation, SHAP, report + heat map, repo/environment, decisions-and-corrections, open-questions, glossary). Read the pages relevant to the current step; read `rents/wiki/decisions-and-corrections.md` to avoid repeating past mistakes. When anything changes or is learned, update the relevant wiki page AND append to `decisions-and-corrections.md`. Short schedule: `rents/docs/PLAN.md`. API notes: `rents/docs/README.md`. Full API spec: `rents/docs/openapi.json` (parse with Python, `encoding='utf-8'`).

Key facts (details in the wiki): freeze modelling 14:15, submit by 14:45; safety baseline CSV committed by ~12:15; recommended model = LightGBM on log rent (L1/Huber), baseline first; date split (build < 1 Jun, check 1 Jun-31 Jul) and NO tuning on the check pile; report leads with insights; heat map (OpenStreetMap + filters + median/mean) only after/parallel to submission; ask organisers about submission channel and retraining on the check pile; the input CSV has 33 suburbs vs 29 in the API.

Hard rules:
- Use only information dated by **31 Jul 2026**. Never use adverts after that to build or tune. Never use `listings/for-rent`.
- Output `rents_<team>.csv`: `gnaf_id`, `rent_with_car_space`, `rent_without_car_space`; exactly 65,777 ids, no blanks. Blank answers are penalised more than wrong ones, so always fall back to a suburb median.
- Private day-of files (past leases, census blocks) must not be committed or republished: keep them out of git.
- Deliver `report.html` with insights first, then held-out median abs error, share within $100, R², the date split, data and method.

API:
- Env vars (see `.env.example`): `MICROBURBS_API_KEY`, `MICROBURBS_API_BASE`. Never print, log or commit the key; `.env` is gitignored.
- ~10 req/s per key; retry on 429 using `Retry-After`; cache every response to disk.
- Prefer suburb-level bulk endpoints (`listings/rent-history` with `to_date=2026-07-31`, `properties`) over per-flat calls (65,777 calls ≈ 110 min per endpoint).
- `data: null` with HTTP 200 means no data; handle it.
- Suburb names must be exact SAL names (e.g. `Glebe (NSW)`); use `/v1/geocode/suburb`.

Fetcher: `rents/fetcher.py` (cached, rate-limited, leakage-guarded; usage in `rents/docs/README.md`). Tests: `cd rents && python -m pytest -q`. Advert rows: `gnaf_pid, weekly_rent, listing_date, bedrooms, bathrooms, car_spaces, leased, lat, lng`.

Reference doc: https://claude.ai/artifact/AV1YQ6NgxrooHnKmq6wVWc
