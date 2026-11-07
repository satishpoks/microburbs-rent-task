"""Which factors drive the submitted model (v2: best variant from model_v2.py)? Gain share + mean |SHAP| (log-rent points) per feature and per factor group.
Run: python src/04_feature_impact.py   (re-runs model_v2.py first, ~4 min). SHAP is computed on recent BUILD-pile adverts only (not the check pile)."""
import runpy
from pathlib import Path

import numpy as np
import pandas as pd
import shap

g = runpy.run_path(str(Path(__file__).resolve().parent / "03_model_v2.py"))
model, Xbest, BEST, build, resid, OUT = g["final_model"], g["Xbest"], g["BEST_FEATS"], g["build"], g["resid"], g["OUT"]
pd.set_option("display.width", 200)

recent = (build.listing_date >= "2025-06-01").values
X = Xbest[recent].reset_index(drop=True)
sample = X.sample(min(4000, len(X)), random_state=0)
sv = shap.TreeExplainer(model).shap_values(sample)
mabs = pd.Series(np.abs(sv).mean(axis=0), index=BEST)
gain = pd.Series(model.feature_importance("gain"), index=BEST)
df = pd.DataFrame({"gain_%": gain / gain.sum() * 100, "shap_%": mabs / mabs.sum() * 100, "mean_abs_shap_logpts": mabs}).sort_values("shap_%", ascending=False)
df["approx_±%_rent"] = (np.exp(df.mean_abs_shap_logpts) - 1) * 100

GROUPS = {
    "Market level & momentum": ["level_lag", "level_n", "mom3", "mom6", "mom_city6", "growth_est", "level_prev"],
    "Flat's own rent history": ["prev_lr", "adj_prev", "prev_gap", "prev_cnt", "own_nrm", "own_nrm_n"],
    "Building premium": ["bldg_rel", "bldg_n", "b_same_nrm", "b_same_n", "b_any_nrm", "b_any_n"],
    "Neighbourhood (250/500 m) premium": [c for c in BEST if c.startswith("nb")],
    "Location (suburb, coordinates)": ["suburb", "lat", "lng"],
    "Flat size & type": ["bedrooms", "bathrooms", "beds_x_baths", "baths_per_bed", "prop"],
    "Parking": ["car"],
    "Building / block context": ["floor_level", "flats_in_building", "block_homes_2026", "block_new_homes_2021_2026"],
}
grp = pd.Series({k: df.loc[[c for c in v if c in df.index], "shap_%"].sum() for k, v in GROUPS.items()}).sort_values(ascending=False)
grp_gain = pd.Series({k: df.loc[[c for c in v if c in df.index], "gain_%"].sum() for k, v in GROUPS.items()})
print("\n=== FEATURES (sorted by mean |SHAP|) ===")
print(df.round(2).to_string())
print("\n=== FACTOR GROUPS ===")
print(pd.DataFrame({"shap_%": grp, "gain_%": grp_gain.reindex(grp.index)}).round(1).to_string())
df.round(4).to_csv(OUT / "feature_impact.csv")
