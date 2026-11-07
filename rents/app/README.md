# Sydney Rent Estimator (local app)

Interactive rent estimator on top of our LightGBM v2 predictions (rents/output/rents_d4data.csv).

- **Find my flat:** address search -> the model's prediction for that exact flat (with / without car space), a likely range, comparables and charts.
- **Describe a property:** suburb, type, bedrooms, bathrooms, floor band, building size, map radius, parking -> estimate = median of the model's predictions for matching real flats (filters widen automatically when matches are scarce).
- **Map:** OpenStreetMap with a rent heat map (median predicted rent per 150-800 m square), individual flats, or both.

Run: `python rents/app/build_data.py` (creates data.js from main_data + the predictions), then `cd rents/app && python -m http.server 8765` and open http://127.0.0.1:8765/ (opening index.html directly also works). Map tiles and Leaflet need internet; everything else works offline.
Tests of the logic: `node -e` against core.js (pure functions, no DOM).

`data.js` holds our model's predicted rents for the 65,777 input flats (no lease rents, no census files). It is committed so the app can be deployed.

## Deploy on Vercel (static)
Import the GitHub repo in the Vercel dashboard, set **Root Directory** to `rents/app`, Framework Preset **Other**, leave Build Command and Output Directory empty. `vercel.json` adds a noindex header; `.vercelignore` keeps build_data.py and this README out of the deployment.
