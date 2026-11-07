# Data and geography

## Files (competition day)
| File | Visibility | Content |
| --- | --- | --- |
| `rents-input-flats-city-of-sydney.csv` | public | 65,777 flats, 33 suburbs, `gnaf_id` (columns beyond that NOT yet seen: check for beds/baths/parking/mesh block/coords) |
| `rents-past-leases-city-of-sydney.csv` | **private** | historic adverts (training signal) |
| `blocks-homes-and-people-2021-2026.csv` | **private** | 2021 Census counts + 2026 estimates per mesh block |
Private data goes ONLY in `rents/data/` (gitignored). The GitHub repo is public.

## The 29 vs 33 suburb discrepancy (UNRESOLVED)
The task page says the input has **33 suburbs**; the API docs list **29** City of Sydney suburbs. The 4 extra suburbs may be outside API coverage (API returns 403) or a different counting of suburbs/localities. On the day: list the distinct suburbs in the input CSV, compare to the 29, and plan fallbacks (private past-leases file, nearest-suburb medians) for any not covered.

## The 4,246 addresses
Absent from the City address and block files, but must still get predictions (keep all 65,777 rows). They will have no census-block features -> need fallbacks (suburb-level medians or coordinates-based neighbours). Count them early.

## G-NAF ids
G-NAF = Geocoded National Address File, the official address database. Ids look like `GANSW705970502`. In the API's suburb endpoints the field is `gnaf_pid`; in the task CSV it is `gnaf_id`.

## ABS mesh blocks
- The smallest geographic unit of the Australian Bureau of Statistics: a small patch of land (often one city block); in inner Sydney typically a few dozen homes. Every address sits in exactly one; code is an 11-digit string (example `11205253900`).
- In the API: `properties` rows carry `mb`; also `GET /v1/mbs/list?sal=...`, `/v1/mbs/{mb_code}/profile`, `shapes/mesh-blocks`, `crime/by-mesh-block`, `development/construction-activity`, `market/vacancy-map` (per mesh block).
- Join path: flat -> `mb` code -> row in `blocks-homes-and-people-2021-2026.csv` (counts of homes and people, 2021 census + 2026 estimates; check column names on the day). Useful for density and growth features, finer than suburb.
- Treat codes as strings (leading digits, avoid float conversion).
- Check on the day whether the input CSV already has the block code; otherwise get it from `properties`.

## Join keys and traps
- gnaf id: `gnaf_id` (CSV) = `gnaf_pid` (suburb endpoints) = `{gnaf_id}` (per-flat path).
- Two rent record shapes (suburb vs per-flat), see api.md.
- Scored rent uses the advert's parking; if blank, the input's parking is used -> the car-space handling matters for evaluation too.
- Adverts are for dwellings of all types; the task is about flats (units/apartments) - filter or use `property_type` as a feature, decide after inspecting.

## G-NAF reference data (added 7 Nov 2026)
- Local download: `Additional Data/g-naf_aug26_allstates_gda2020_psv_110/` (G-NAF Aug 2026, **NSW files only**, 2.5 GB, gitignored, open data but never commit).
- Slim table: `python rents/build_gnaf_slim.py` (~2 min, stdlib only) -> `rents/data/gnaf_nsw_slim.csv.gz` (gitignored), 5,224,340 current NSW addresses, none retired, all with lat/lng and 2021 + 2016 mesh block. Columns: gnaf_id, locality, postcode, street, number, flat_type, flat_number, level_number, building_name, lat, lng, mb2021, mb2016, property_pid, primary_secondary, date_created.
- Uses: validate input `gnaf_id`s, explain the 33 vs 29 suburbs, and fill coordinates, mesh block, flat type, level and building for the 4,246 addresses missing from the City files. No rents, beds, baths or car spaces in G-NAF.
- Ignore rows with `date_created` after 2026-07-31 if they would be used as features.
- Mesh block codes are strings; `mb2021` matches the ABS 2021 MB code.

## Free external data sources (noted 7 Nov 2026, not yet used)
Candidate public sources for extra features or checks. Nothing here is fetched yet; check each against the 31 Jul 2026 cut-off and the task rules before using.
- data.gov.au
- Digital Atlas of Australia
- Released ABS Census data
- NSW Spatial Services
- NSW Planning Portal open DA (development application) data since 2019
- City of Sydney open data
- NSW Valuer General bulk sales
- Digital Earth Australia
- OpenStreetMap
- Overture Maps
- Mapillary
