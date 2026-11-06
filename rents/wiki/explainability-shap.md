# Explainability: feature importance and SHAP

Purpose: feed the "lead with insights" section of `report.html` and sanity-check the model. It is a REPORTING step after the model is built and checked; it does not change predictions.

## Options
1. **Built-in LightGBM importance** - quick, but biased toward features with many distinct values.
2. **SHAP values (preferred)** - exact for tree models (TreeSHAP). For each flat: prediction = base value (the model's average) + one contribution per feature. Averaging absolute contributions gives a ranked list of drivers. LightGBM can also output contributions directly: `predict(X, pred_contrib=True)`; the `shap` library supports LightGBM and XGBoost.
3. Dependence plots: feature vs its SHAP value (shape of effect: floor level, distance to CBD, flats in building).
4. Car-space premium: difference between the two predictions per flat, summarised by suburb.

## Units correction
SHAP contributions are in the model's output units. If we train on **log rent**, they are log effects (~percentage effects: "Pyrmont adds ~8%"), NOT dollars. Earlier Claude said "dollars" - corrected. For the report either convert (multiply back) or show percentages, or train on raw dollars.

## What to show in the report
- Top-10 drivers (mean |SHAP|) bar chart; 1-2 dependence plots; car-space premium by suburb; maybe biggest building/suburb surprises.
- Caveats to state: importance describes the MODEL, not cause and effect ("each storey adds $5" = pattern the model learned); overlapping features (suburb, coordinates, building) share credit unpredictably - do not over-read small differences.

## Libraries
`shap` not verified installed; install on the day if wanted (`pip install shap`). Runtime on ~65k rows with a tree model is fine; sample if slow.
