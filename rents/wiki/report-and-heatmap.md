# Report (`report.html`) and heat map

## `report.html` (required deliverable)
Order: (1) **Insights first** (what we learned: car-space premium by suburb, rent per bedroom, outlier buildings, top drivers from SHAP); (2) **held-out accuracy**: median absolute error, share within $100, R squared, vs baseline $86 / 55.21%; (3) **how adverts were split by date** (exact cut-off, build vs check pile sizes); (4) **data and method** (endpoints, supplied files, any other open data with rights, features, model, tuning inside build pile, fallbacks, whether the check pile was used for final training). Generate it from a template so metrics fill in automatically. Do not embed private-file contents.

## Heat map for the presentation (nice-to-have; NOT before 15:00)
Goal: make the output usable for people. Static page built from OUR predictions (never the private files).
- Base map: **OpenStreetMap tiles via Leaflet**; heat layer with `leaflet.heat`, or coloured mesh-block/suburb polygons (easier to read; polygons from `shapes/mesh-blocks` / `shapes/boundary` or ABS, check licence). Check OpenStreetMap's tile usage policy for public/heavy use; use another provider if needed.
- Data: one JSON built from the final CSV joined to coordinates (`lat`/`lng` from the `properties` endpoint), suburb, beds, baths, mesh block.
- **Filters:** suburb, bedrooms, bathrooms, with / without car space, **median vs mean** toggle, maybe price range.
- Readout on click/hover: median or mean rent, number of flats it is based on, and a range (e.g. 25th-75th percentile).
- Honesty: label values as **model estimates, not listed rents**; show sample sizes so thin areas don't look more certain than they are; grey out cells with very few flats.
- Reuse: the repo's `nextjs-suburb-map` demo already has Leaflet-style map code; `streamlit-property-explorer` is an alternative quick UI.
- Scheduling: teammate builds it in parallel on fake data tonight/tomorrow morning; only the final CSV is dropped in. Presentation time unknown - ask.
