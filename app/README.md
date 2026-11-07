# Sydney Rent Estimator (static app)

Interactive front end for the d4data predictions in `submission/rents_d4data.csv`. Live: https://d4data-rent-estimator.vercel.app/

- **Find my flat:** address search -> the model's prediction for that exact flat (with / without car space), a likely range, comparables and charts.
- **Describe a property:** suburb, type, bedrooms, bathrooms, floor band, building size, map radius, parking -> estimate = median of the model's predictions for matching real flats (filters widen automatically when matches are scarce).
- **Map:** OpenStreetMap with a rent heat map (median predicted rent per 150-800 m square), individual flats, or both.

Run locally: `python src/08_build_app_data.py` (rebuilds `app/data.js` from `data/` + the predictions), then `cd app && python -m http.server 8765` and open http://127.0.0.1:8765/ (opening `index.html` directly also works). Map tiles and Leaflet need internet; everything else works offline.

`data.js` holds only our model's predicted rents for the 65,777 input flats (no lease rents, no census rows). `core.js` is pure logic (no DOM) so it can be tested with `node`.

## Deploy on Vercel (static)
Import the GitHub repo, set **Root Directory** to `app`, Framework Preset **Other**, leave Build Command and Output Directory empty. `vercel.json` adds a noindex header; `.vercelignore` keeps this README out of the deployment.
