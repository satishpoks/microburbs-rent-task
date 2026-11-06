# Rent task – notes (Microburbs hackathon, Sat 7 Nov 2026)

Task page: https://www.microburbs.com.au/p/hackathon-task-rents
API docs (JS-rendered): https://api-ht.microburbs.com.au/docs
Spec (saved here): `openapi.json` – fetched 2026-11-06 from https://api-ht.microburbs.com.au/openapi.json
Reference doc (Claude Docs): https://claude.ai/artifact/AV1YQ6NgxrooHnKmq6wVWc

## Task
Estimate weekly rent for 65,777 City of Sydney flats (33 suburbs), with and without a car space.

- Deliverables: `rents_<team>.csv` (`gnaf_id`, `rent_with_car_space`, `rent_without_car_space`; all 65,777 ids, no extras, no blanks) and `report.html` (insights first, then held-out median abs error + R², date-split method, data and method).
- Scoring: median absolute $ error on 1,699 adverts dated 1 Aug–30 Sep 2026; tie-break = share within $100. Baseline: $86 error, 55.21% within $100. Blank answers score worse than wrong ones.
- Constraints: use only information dated by **31 Jul 2026**. Never use later adverts to build or tune. `listings/for-rent` is forbidden. Private files (past leases, census blocks) are day-of only and must not be republished.
- Files go in at **11am Sat 7 Nov**; submission channel not stated – ask organisers.

## API essentials
- Base `https://api-ht.microburbs.com.au`; header `Authorization: Bearer $MICROBURBS_API_KEY` (or `X-Api-Key`). Key is issued on the day. Free. `GET /v1/me` checks the key.
- Limit ~10 req/s per key; 429 → wait `Retry-After`. 401 bad key; 403 outside City of Sydney.
- Envelope: `{data: ...}`; no data = HTTP 200 with `data: null`, `reason`, `message`. Always branch on `data`.
- Suburb names must be exact SAL names (e.g. `Glebe (NSW)`); resolve with `GET /v1/geocode/suburb?q=`.

## Fetch plan (bulk, not per flat)
Per-flat = 65,777 calls ≈ 110 min per endpoint at 10 req/s. Prefer suburb endpoints (29 suburbs, `limit` up to 1000, page with `offset`, total in `meta.total`):
1. `GET /v1/suburbs/{name}/listings/rent-history?to_date=2026-07-31&limit=1000&offset=N` – rent, listing date, beds, baths, car spaces, leased flag, coords.
2. `GET /v1/suburbs/{name}/properties?limit=1000&offset=N` – every address: beds, baths, car spaces, floor, flats in building.
3. Per-flat `rent-history` / `history/all` / `basics/all` only for gaps. Cache everything to disk; retry 429.
4. Suburb context: `market/median-rent-series`, `rent-map`, `vacancy-rate`, `bedroom-stats`, `yield-pct`. Check each series' dates and cut at 31 Jul.

## Open questions
- Exact advert field names (spec has descriptions, not response schemas) – look at the first real response.
- Whether suburb-level `listings/rent-history` is acceptable for the leaderboard run – confirm with organisers.

## Plan
1. Fetch + cache (start immediately when the key arrives).
2. Time split: train < ~1 Jun 2026, validate 1 Jun–31 Jul. Never tune on later data.
3. Baseline: suburb × beds × baths median with fallback chain → write a valid CSV early as the safety submission.
4. Model: gradient boosting on log rent, MAE/Huber; predict twice (parking 1 / 0), enforce with ≥ without; add building/own-history and trend features, census block features.
5. Validator (65,777 unique ids, no blanks), then `report.html`.
