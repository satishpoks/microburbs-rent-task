# Microburbs hackathon API

- Base: `https://api-ht.microburbs.com.au` (env `MICROBURBS_API_BASE`). Docs page `.../docs` is JavaScript-rendered (a plain fetch returns empty). The machine-readable spec is `.../openapi.json`; **saved in this repo at `rents/docs/openapi.json`** (fetched 2026-11-06, ~1.1 MB; parse with Python `encoding='utf-8'`).
- The Chrome extension was NOT connected when we tried to open the docs page, so the docs page itself was never viewed in a browser; everything comes from the spec. The spec's intro text matches the docs page content (same worked example/limits) but equality was not verified line by line.
- A Claude Docs reference document was also made: https://claude.ai/artifact/AV1YQ6NgxrooHnKmq6wVWc (note: it still lists "advert field names" as an open question; the answer is below).

## Auth, limits, errors
- Key: one per team, issued on competition day (NOT available before). Header `Authorization: Bearer <key>` or `X-Api-Key`. Calls are free. `GET /v1/me` = which team the key is for.
- Rate limit ~**10 requests/second per key**, short bursts allowed. `429` -> wait `Retry-After`. `401` bad/missing key. `403` outside hackathon area (or endpoint not in this API).
- Every response has `X-Request-Id` (quote it when asking for help: david@microburbs.com.au or the team at the event). Most answers cached server-side.
- Envelope: success `{"data": ...}`. **No data is still HTTP 200**: `{"data": null, "available": false, "reason": "...", "message": "..."}`. Always branch on `data` not being null.

## Coverage
City of Sydney LGA only: **29 suburbs**, ~209,000 G-NAF ids. Exact SAL names (state suffix matters): Alexandria, Barangaroo, Beaconsfield (NSW), Camperdown (NSW), Centennial Park (NSW), Chippendale, Darlinghurst, Darlington (Sydney - NSW), Dawes Point, Elizabeth Bay, Erskineville, Eveleigh, Forest Lodge, Glebe (NSW), Haymarket, Millers Point, Moore Park, Potts Point, Pyrmont, Redfern, Rosebery (NSW), Rushcutters Bay, Surry Hills, Sydney, The Rocks (Sydney - NSW), Ultimo, Waterloo (NSW), Woolloomooloo, Zetland. Resolve free text with `GET /v1/geocode/suburb?q=`; address -> id with `GET /v1/geocode/address?address=`.
Worked example in the docs: 26 Tudor Street, Surry Hills = `GANSW705970502`.
NOTE: the input CSV spans **33 suburbs** vs 29 here - see data-and-geography.md.

## Endpoints that matter for rent
Suburb bulk (preferred):
- `GET /v1/suburbs/{suburb}/listings/rent-history?from_date&to_date&limit(<=1000)&offset` - "every rental advert we hold for the suburb, live or long gone, newest first". `to_date` default is TODAY (so would include post-cutoff). `meta.total` = count before paging.
- `GET /v1/suburbs/{suburb}/properties?limit(<=1000)&offset` - every address ordered by G-NAF id with beds, baths, car spaces, floor, flats in building, mesh block, coordinates.
- Suburb context: `market/median-rent`, `median-rent-series` (check dates!), `rent-map`, `yield-pct(-series)`, `vacancy-rate(-series)`, `bedroom-stats`, `days-on-market`, `months-of-supply`, `strata-levies`, `demographics/*`, `lifestyle/*`, `crime/*`.
- `listings/for-rent` = live listings = **FORBIDDEN by the task**.
Per flat (`/v1/properties/{gnaf_id}/...`): `rent-history`, `rent-history-latest`, `history/all` (expensive bundle), `basics/all` (beds, baths, parking, type, land), `valuation/avm`, `street/profile`, `comparables/*`, `neighbours`, `surroundings/*`, `transport/nearby`, `amenities/nearby`, `risks/*`, `context/street-bedroom-series`. `context/nearby-for-sale`: check dates before any use.
Other: `/v1/mbs/...` (mesh blocks), `/v1/lga/...`, `/v1/sa4/...`, `/v1/area-stats/...` (census), `/v1/suburbs/finder/*`.

## Response shapes (from the spec's examples)
Suburb `listings/rent-history` -> `data: {area_level, area_name, meta:{limit,offset,returned,total}, results:[{address, bathrooms, bedrooms, car_spaces, gnaf_pid, lat, lng, leased, listing_date, property_type, weekly_rent}]}`. **The example row is dated 2026-10-28** (post-cutoff data exists in the system).
Suburb `properties` -> same envelope; rows `{address, bathrooms, bedrooms, car_spaces, dwelling_type, flats_in_building, floor, gnaf_pid, lat, lng, level, mb, property_type}` (`mb` e.g. "11205253900").
Per-flat `rent-history` -> `data: [{date, price?, type:"For Rent", address}]` newest first; `price` can be missing (record with no price is legitimate).
Per-flat `rent-history-latest` -> single object of the same shape.
Field-name difference to remember: suburb endpoint uses `gnaf_pid`, `weekly_rent`, `listing_date`; per-flat uses `date`, `price`; the task CSV uses `gnaf_id`.

## Gotchas
- Not verified against the live API (no key yet): retry behaviour, page sizes, real field availability, whether `to_date` filters as documented.
- Suburb names with spaces/parentheses must be URL-encoded (the quickstart client does it).
- Windows console is cp1252: printing spec text with arrows crashes Python; use `sys.stdout.reconfigure(encoding='ascii', errors='replace')`.
