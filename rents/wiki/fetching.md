# Fetching strategy and the fetcher

## The time maths (corrected)
- Per-flat calls: 65,777 flats / 10 req/s = **~6,580 s = ~110 min per endpoint**. (Claude first said "about 11 minutes" - WRONG, corrected.)
- Suburb bulk calls: 29 suburbs, up to 1,000 rows/page -> a few hundred calls total (the spec example shows one suburb, Waterloo, with 16,420 adverts and 12,620 addresses -> ~17 + ~13 pages).
- So: fetch adverts + properties by suburb; use per-flat calls only to fill gaps.

## Fetch order on the day
1. `python rents/fetcher.py adverts` (always sends `to_date=2026-07-31`).
2. `python rents/fetcher.py properties`.
3. Optional gap fill: `python rents/fetcher.py flats ids.txt` (one gnaf_id per line).
4. Suburb context series if wanted (`median-rent-series`, `vacancy-rate-series`, etc.) - drop values dated after 31 Jul.
Run from the repo root with `MICROBURBS_API_KEY` in env/`.env`. Outputs land in `rents/data/*.jsonl` (gitignored); cache in `rents/cache/responses.sqlite` (gitignored).

## `rents/fetcher.py` (written + tested; 19 tests, no network)
- Wraps the existing `python-quickstart/microburbs_client.py` client (Bearer auth, URL-encoding, unwraps `{"data":...}`, retries 429/5xx honouring `Retry-After`).
- Adds: shared `RateLimiter` (default 8 req/s, `--rate`), SQLite `DiskCache` (caches `None` answers too; errors are NOT cached; reruns cost zero API calls), `paged()` over `{results, meta.total}`, `rent_adverts()`, `properties()`, `flat_rent_history()`, `flat_rent_histories()` (8 threads, de-dupes ids).
- **Leakage guard:** `rent_adverts()` raises `LeakageError` if `to_date` is after 2026-07-31 or None; it also drops any returned row with `listing_date` after the cutoff or missing (`stats["dropped_after_cutoff"]`). `flat_rent_history()` drops records dated after the cutoff or without a date.
- `SUBURBS` constant = the 29 API suburbs. `--suburbs` overrides.
- Verified with a stubbed HTTP session through the real quickstart client: a 429 was retried, 1,200 rows paged in 2 calls, URL was `.../v1/suburbs/Glebe%20%28NSW%29/listings/rent-history?limit=1000&offset=0&to_date=2026-07-31`, rerun made 0 calls.
- NOT yet tested against the real API.

## Things to check on first real response
- Do adverts carry `weekly_rent` for all rows? How many have `car_spaces` null? `leased` meaning?
- Date range per suburb; any duplicates (same gnaf_pid re-advertised) - decide how to treat them.
- Whether rents look weekly (not monthly) and whether obvious outliers exist.
- Whether the 33-suburb input list includes suburbs the API refuses (403) - see data-and-geography.md.
