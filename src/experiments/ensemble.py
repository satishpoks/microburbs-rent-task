"""Ensemble of the 5 LightGBM variants x 3 seeds (geometric mean of predictions), fitted on the BUILD pile only.

Run: python src/experiments/ensemble.py   (re-runs model_v2.py first for the features/variants, ~4 min, then fits the extra models)
Promotion rule, fixed BEFORE running: promote the ensemble to rents_d4data.csv only if
  (a) its inner-slice median error (Apr-May, inside the build pile) <= the best single variant's inner-slice error, and
  (b) its check-pile median error is not worse than the current v2 by more than $1.5.
The check pile is scored once; nothing is tuned on it. Only the default split may touch the submission file.
"""
import json
import runpy
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

g = runpy.run_path(str(Path(__file__).resolve().parents[1] / "03_model_v2.py"))
variants, inner, Xc, scored, build, inp = g["variants"], g["inner"], g["Xc"], g["scored"], g["build"], g["inp"]
yb, w, params, score, OUT, safety = g["yb"], g["w"], g["params"], g["score"], g["OUT"], g["safety"]
build_features, ex_fin, fin, DEFAULT_SPLIT = g["build_features"], g["ex_fin"], g["fin"], g["DEFAULT_SPLIT"]
iv, yv = g["iv"], g["yv"]
SEEDS = [7, 11, 23]
PREV_V2_MED = 44.09


def pred_log(m, X, resid):
    return m.predict(X) + (X.level_lag.values if resid else 0.0)


# ---------------------------------------------------------------- inner slice: ensemble of the 5 variants (seed 7) vs each single variant
P = {n: pred_log(inner[n][0], variants[n][0][iv], variants[n][1]) for n in variants}
ens_inner = np.exp(np.mean(list(P.values()), axis=0))
m_ens_inner = score(yv[iv], ens_inner)
best_single = min(inner[n][1]["median_abs_error"] for n in inner)
print("inner slice (Apr-May, inside the build pile):")
for n in variants: print(f"  {n:22s} ${inner[n][1]['median_abs_error']:.1f}  within100 {inner[n][1]['within_100']:.3f}  r2 {inner[n][1]['r2']:.3f}")
print(f"  {'ENSEMBLE (5 variants)':22s} ${m_ens_inner['median_abs_error']:.1f}  within100 {m_ens_inner['within_100']:.3f}  r2 {m_ens_inner['r2']:.3f}")

# ---------------------------------------------------------------- final fits on the whole build pile: 5 variants x 3 seeds
fin_models = []
for n, (X, resid) in variants.items():
    rounds = int(inner[n][0].best_iteration * 1.05)
    off = X.level_lag.values if resid else 0.0
    for sd in SEEDS:
        m = lgb.train({**params, "seed": sd}, lgb.Dataset(X, yb - off, weight=w), num_boost_round=rounds)
        fin_models.append((n, list(X.columns), resid, m))
    print(f"fitted {n} x {len(SEEDS)} seeds ({rounds} rounds)")


def ensemble_predict(Xfull):
    logs = [pred_log(m, Xfull[cols], resid) for _, cols, resid, m in fin_models]
    return np.exp(np.mean(logs, axis=0))


# ---------------------------------------------------------------- check pile, scored once
pc = ensemble_predict(Xc)
m_ens = score(scored.weekly_rent.values, pc)
print("ENSEMBLE on the check pile (scored once):", {k: round(v, 3) for k, v in m_ens.items()})
print(f"current v2 on the check pile: median error ${PREV_V2_MED}  (v1 $46.5)")

# ---------------------------------------------------------------- final predictions for all flats
preds = {}
for name, car in [("without", 0.0), ("with", 1.0)]:
    Xf = pd.concat([build_features(fin.assign(car=car), build).reset_index(drop=True), ex_fin], axis=1)
    preds[name] = ensemble_predict(Xf)
ens = pd.DataFrame({"gnaf_id": inp.gnaf_id, "rent_with_car_space": np.round(np.maximum(preds["with"], preds["without"])), "rent_without_car_space": np.round(preds["without"])})
bad = ~np.isfinite(ens[["rent_with_car_space", "rent_without_car_space"]]).all(axis=1) | (ens.rent_without_car_space <= 0)
ens.loc[bad, ["rent_with_car_space", "rent_without_car_space"]] = safety.loc[bad, ["rent_with_car_space", "rent_without_car_space"]].values
ens.to_csv(OUT / "lightgbm_ensemble.csv", index=False)
prem = ens.rent_with_car_space - ens.rent_without_car_space
print(f"fallback rows: {int(bad.sum())} | car premium $/wk median {prem.median():.0f}, p10 {prem.quantile(.1):.0f}, p90 {prem.quantile(.9):.0f}")

cond_a = m_ens_inner["median_abs_error"] <= best_single
cond_b = m_ens["median_abs_error"] <= PREV_V2_MED + 1.5
promote = DEFAULT_SPLIT and cond_a and cond_b
print(f"promotion rule: (a) inner <= best single: {cond_a} | (b) check within $1.5 of v2: {cond_b} | default split: {DEFAULT_SPLIT} -> promote: {promote}")
if promote:
    f = ens.copy()
    for c in ["rent_with_car_space", "rent_without_car_space"]: f[c] = f[c].fillna(safety[c])
    assert len(f) == 65_777 and f.gnaf_id.is_unique and set(f.gnaf_id) == set(inp.gnaf_id) and f.notna().all().all()
    assert (f.rent_without_car_space > 0).all() and (f.rent_with_car_space >= f.rent_without_car_space).all()
    f.to_csv(g["SUB"] / "rents_d4data.csv", index=False)
    print("PROMOTED ensemble to rents_d4data.csv")
else:
    # model_v2 already re-promoted v2 (or left the file alone); make sure it is not v1
    print("ensemble not promoted: rents_d4data.csv stays as written by model_v2.py")
metrics = json.load(open(OUT / "metrics.json"))
metrics.update({"ensemble": m_ens, "ensemble_inner": m_ens_inner, "ensemble_promoted": bool(promote), "winner": "lightgbm_ensemble" if promote else metrics.get("winner")})
json.dump(metrics, open(OUT / "metrics.json", "w"), indent=2)
