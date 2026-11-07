"""Aggregate numbers for submission/report.html (no per-advert rows are written).
Run: python src/05_report_stats.py   (re-runs model_v2.py first, ~4 min; check pile scored from the already-built final model, nothing tuned)"""
import json
import runpy
from pathlib import Path

import numpy as np
import pandas as pd

g = runpy.run_path(str(Path(__file__).resolve().parent / "03_model_v2.py"))
scored, pc, build, leases, OUT = g["scored"].copy(), g["pc"], g["build"], g["leases"], g["OUT"]
S = {}
scored["pred"] = np.asarray(pc); scored["err"] = scored.pred - scored.weekly_rent; scored["abs"] = scored.err.abs()
a = scored["abs"]
S["check"] = {"n": int(len(scored)), "median_abs_error": round(float(a.median()), 1), "within_100": round(float((a <= 100).mean() * 100), 1),
              "r2": round(float(1 - (scored.err ** 2).sum() / ((scored.weekly_rent - scored.weekly_rent.mean()) ** 2).sum()), 3),
              "buckets": {"0-50": int((a <= 50).sum()), "50-100": int(((a > 50) & (a <= 100)).sum()), "100-200": int(((a > 100) & (a <= 200)).sum()), "200+": int((a > 200).sum())},
              "median_signed_pct": round(float((scored.err / scored.weekly_rent * 100).median()), 1)}
S["check_by_parking"] = {k: {"n": int(len(v)), "median_abs_error": round(float(v["abs"].median()), 1), "within_100": round(float((v["abs"] <= 100).mean() * 100), 1)}
                         for k, v in {"with car space": scored[scored.car_state == 1], "without car space": scored[scored.car_state == 0]}.items()}
S["check_by_beds"] = {}
for b in [0, 1, 2, 3]:
    v = scored[scored.bedrooms == b]
    S["check_by_beds"][str(b)] = {"n": int(len(v)), "median_abs_error": round(float(v["abs"].median()), 1), "within_100": round(float((v["abs"] <= 100).mean() * 100), 1)}
S["split"] = {"n_build": int(len(build)), "build_from": str(build.listing_date.min().date()), "build_to": str(build.listing_date.max().date()),
              "n_check_all": int(len(g["g"]["check"])), "check_from": str(g["g"]["check"].listing_date.min().date()), "check_to": str(g["g"]["check"].listing_date.max().date()),
              "n_leases_raw_rows": int(len(pd.read_csv(g["g"]["DATA"] / "rents-past-leases-city-of-sydney.csv", usecols=["gnaf_id"]))),
              "n_dropped_flagged": int(pd.read_csv(g["g"]["DATA"] / "leases_flagged.csv", usecols=["drop_candidate"]).drop_candidate.sum())}

# parking premium in matched groups (suburb x bedrooms), last 12 months of the build pile, >=10 adverts per parking state
w = build[(build.listing_date >= "2025-06-01") & build.car_space.notna() & build.bedrooms.between(0, 3)].copy()
w["has_car"] = (w.car_space > 0).astype(int)
grp = w.groupby(["suburb", "bedrooms", "has_car"]).weekly_rent.agg(["median", "size"]).unstack("has_car")
ok = grp[(grp[("size", 0)] >= 10) & (grp[("size", 1)] >= 10)]
prem = ok[("median", 1)] - ok[("median", 0)]
S["parking"] = {"window": "2025-06-01 to 2026-05-31", "groups": int(len(ok)), "median_premium": round(float(prem.median()), 0), "median_premium_pct": round(float((ok[("median", 1)] / ok[("median", 0)] - 1).median() * 100), 1),
                "share_groups_positive": round(float((prem > 0).mean() * 100), 0), "adverts": int(len(w))}
one = ok.xs(1, level="bedrooms")
one = one.assign(vol=one[("size", 0)] + one[("size", 1)]).sort_values("vol", ascending=False).head(4)
S["parking_1bed"] = [{"suburb": s.replace(" (NSW)", ""), "no_car": round(float(r[("median", 0)])), "with_car": round(float(r[("median", 1)])), "n_no": int(r[("size", 0)]), "n_with": int(r[("size", 1)])} for s, r in one.iterrows()]
json.dump(S, open(OUT / "report_stats.json", "w"), indent=2)
print(json.dumps(S, indent=1))
