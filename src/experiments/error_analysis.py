"""Error analysis on the INNER validation slice (Apr-May 2026, inside the build pile). The check pile (1 Jun-31 Jul) is not touched.
Run: python src/experiments/error_analysis.py   (re-runs baseline.py first, ~1 min, to get the inner model and features)"""
import runpy
from pathlib import Path

import numpy as np
import pandas as pd

g = runpy.run_path(str(Path(__file__).resolve().parents[1] / "02_baseline.py"))
build, Xb, m_inner, inner_val = g["build"], g["Xb"], g["m_inner"], g["inner_val"]
pd.set_option("display.width", 200); pd.set_option("display.max_columns", 30)

v = build[inner_val].reset_index(drop=True)
X = Xb[inner_val].reset_index(drop=True)
v["pred"] = np.exp(m_inner.predict(X)); v["err"] = v.pred - v.weekly_rent; v["abs"] = v.err.abs(); v["pct"] = v.err / v.weekly_rent * 100
v = pd.concat([v, X[["prev_lr", "prev_gap", "prev_cnt", "bldg_n", "level_n", "flats_in_building"]].reset_index(drop=True)], axis=1)
print(f"inner slice: {len(v):,} adverts | median abs err ${v['abs'].median():.1f} | within $100 {(v['abs'] <= 100).mean():.1%} | median signed % err {v.pct.median():+.1f}% | mean signed $ {v.err.mean():+.1f}")


def seg(name, key):
    t = v.groupby(key, observed=True).agg(n=("abs", "size"), med_err=("abs", "median"), within100=("abs", lambda x: (x <= 100).mean()), bias_pct=("pct", "median"), share_abs_err=("abs", "sum"))
    t["share_abs_err"] = t.share_abs_err / v["abs"].sum()
    print(f"\n--- by {name}"); print(t.round(3).to_string())


v["history"] = np.where(v.prev_lr.notna(), "has own history", "no own history")
seg("own history", "history")
v["gap_bin"] = pd.cut(v.prev_gap, [0, 180, 365, 730, 1460, 5000]).astype(str).where(v.prev_lr.notna(), "none")
seg("age of own previous rent (days)", "gap_bin")
seg("bedrooms", v.bedrooms.clip(upper=4).fillna(-1))
seg("property type", "property_type")
v["parking"] = v.car_space.map({0.0: "no car space", 1.0: "car space"}).fillna("unknown")
seg("parking state of the advert", "parking")
v["bldg_bin"] = pd.cut(v.bldg_n, [-1, 0, 3, 10, 1000]).astype(str)
seg("adverts in same building+beds, prior 12m", "bldg_bin")
v["size_bin"] = pd.cut(v.flats_in_building, [-1, 10, 30, 80, 300, 5000]).astype(str)
seg("flats in building", "size_bin")
v["rent_band"] = pd.cut(v.weekly_rent, [0, 450, 650, 900, 1300, 6000])
seg("actual rent band", "rent_band")
seg("suburb (n>=60)", "suburb")

print("\n--- worst 15 misses (by absolute $)")
cols = ["gnaf_id", "suburb", "bedrooms", "bathrooms", "car_space", "property_type", "weekly_rent", "pred", "err", "prev_gap", "bldg_n"]
print(v.sort_values("abs", ascending=False)[cols].head(15).round(0).to_string(index=False))
print("\nhow much of the total absolute error is in the worst 5% / 10% of adverts:", round(v.sort_values("abs", ascending=False)["abs"].head(int(len(v) * .05)).sum() / v["abs"].sum(), 3),
      round(v.sort_values("abs", ascending=False)["abs"].head(int(len(v) * .10)).sum() / v["abs"].sum(), 3))
