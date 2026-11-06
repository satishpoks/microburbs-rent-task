# microburbs-hackathon-demos

Demo apps for the Microburbs hackathon API (`fastapi-property-report`, `nextjs-suburb-map`, `python-quickstart`, `streamlit-property-explorer`) plus the rent-prediction task in `rents/`.

## Rent task (hackathon day: Sat 7 Nov 2026, files due 11am)
Read `rents/docs/README.md` first: task rules, API essentials, bulk-fetch plan, open questions. The full API spec is saved at `rents/docs/openapi.json` (parse with Python, `encoding='utf-8'`).

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

Reference doc: https://claude.ai/artifact/AV1YQ6NgxrooHnKmq6wVWc
