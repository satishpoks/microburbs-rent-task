# Open questions (ask organisers / check on the day)

| # | Question | Why it matters | Default if no answer |
| --- | --- | --- | --- |
| 1 | How are files submitted (channel/format/upload)? | Page states no channel | Ask at 11:00; plan upload test by 14:00 |
| 2 | May we retrain on the 1 Jun-31 Jul check adverts before predicting? | Rule says never use them "while building or tuning" | Do NOT retrain on the check pile |
| 3 | Is the suburb-level `listings/rent-history` endpoint acceptable for the leaderboard run? | Task page names the per-flat endpoints | Use it (it is in the API) but mention in report |
| 4 | Input has 33 suburbs; API covers 29. Which are the extra 4 and how to treat them? | Predictions needed for all 65,777 flats | Suburb-median / neighbour fallbacks |
| 5 | What columns does the input CSV have (beds, baths, parking, mesh block, coords)? | Determines joins and features | Get beds/baths/mb from `properties` endpoint |
| 6 | Team name for the file name `rents_<team>.csv`? | Required file name | Ask / use registered team name |
| 7 | When is the presentation, and does it need the heat map? | Heat map cannot fit before 15:00 | Build on fake data in parallel |
| 8 | Is team work split (roles)? Who runs the API key? | One key per team, 10 req/s shared | Single fetcher process |
| 9 | Other open data usage rights (if used) | Task allows it with rights | Skip unless clearly licensed |
| 10 | OpenStreetMap tile usage for a public demo | Policy limits heavy use | Use sparingly or other provider |
| 11 | Does the docs page match the spec? (Chrome not connected) | Minor | Compare if Chrome connects |
| 12 | Real API behaviour: `to_date` filtering, page sizes, null handling | Never tested live | Smoke-test first call at 11:00 |
