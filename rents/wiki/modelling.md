# Modelling

## Recommendation: gradient-boosted trees (LightGBM), built in stages
Why: tabular data; captures interactions (beds x suburb, floor x building) without hand-specification; handles missing values; can train on absolute-error objectives matching the scoring metric (median absolute $ error); trains in seconds; explainable with SHAP.
Compared with alternatives: linear regression (rent isn't linear, interactions matter) - fine only as sanity check; random forest (boosting usually lower error); neural nets (too little data / tuning risk for a one-day task); nearest-neighbour "comparables" (good as a FEATURE, weak alone).
LightGBM vs XGBoost: both gradient-boosted trees. LightGBM grows the most useful leaf first (fast, can overfit small data); XGBoost grows level by level (more conservative); LightGBM handles categoricals natively; both have exact TreeSHAP; accuracy near identical at our size. Start with LightGBM; if time allows train an XGBoost (or another seed) and average (small reliable gain).

## Build order
1. **Baseline first:** median rent by suburb x beds x baths with a fallback chain (suburb x beds -> suburb -> overall). Organisers' baseline: $86 median error, 55.21% within $100. This is the safety submission.
2. **Target:** log(weekly rent); objective = absolute error (L1) or Huber; convert back to dollars.
3. **Features, in rough order of payoff:**
   - the flat's OWN latest known rent (before cutoff), grown by the suburb trend since then (strongest signal expected);
   - recent rents in the same building and within a few hundred metres (flats-in-building, coordinates);
   - beds, baths, car spaces, floor, flats in building, property type;
   - suburb, lat/lng;
   - mesh-block census features (day-of file), 2026 estimates;
   - time (advert date / trend) - weight recent adverts more; be careful extrapolating into Aug-Sep.
4. **Car space:** train with car spaces as an input, then predict twice (parking = 1 and 0). Check the premium by suburb is plausible (a rough sanity range guessed earlier: ~$20-80/week depending on area - unverified), and enforce `rent_with_car_space >= rent_without_car_space`. Alternative: estimate premium from adverts differing only in parking.
5. **Fallbacks for flats with no features/history** (incl. the 4,246 missing addresses): suburb x beds medians. Never leave blanks.
6. Predict for ALL 65,777 flats.

## Improving accuracy (priority order)
1. Own-history features. 2. Building/neighbour features. 3. Time trend and recency weighting. 4. Data cleaning (outliers, duplicate adverts, monthly vs weekly rents). 5. Census block features. 6. Car-space handling check. 7. Ensemble (LightGBM + XGBoost/seed). 8. Error analysis: inspect worst misses (on validation folds inside the build pile) by suburb and bedroom count, add features for what is wrong.
Avoid: deep learning; linear model as the final answer.

## Practical notes
- Evaluate with the SAME metric as judging: median absolute error (and share within $100), not just RMSE.
- Evaluate the "scored rent matches the advert's parking" logic: when an advert's parking is blank the input's parking is used, so predictions must be right for the relevant parking state.
- Libraries: pandas was MISSING on this machine; lightgbm/xgboost/shap not verified. Install first (see repo-and-environment.md).
