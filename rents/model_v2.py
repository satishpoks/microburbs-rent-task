"""LightGBM v2: market momentum + neighbour/building features + residual target.

Run: python rents/model_v2.py   (re-runs baseline.py first for shared helpers/data, ~1 min)
Variants are compared on the INNER validation slice (Apr-May 2026, inside the build pile). The check pile (1 Jun-31 Jul) is scored once for the
chosen v2 and compared with v1; nothing is fitted or tuned on it. Final fit uses the build pile only.
"""
import json
import runpy
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parent
g = runpy.run_path(str(ROOT / "baseline.py"))
build, scored, inp, leases = g["build"], g["scored"], g["inp"], g["leases"]
level, window_stats, build_features, rows_from_leases, score = g["level"], g["window_stats"], g["build_features"], g["rows_from_leases"], g["score"]
FEATS1, params, OUT, PRED_DATE, safety, m_lgb_v1 = g["FEATS"], g["params"], g["OUT"], g["PRED_DATE"], g["safety"], g["m_lgb"]
Xb1, tr_rows, inner_val, yb, w = g["Xb"], g["tr_rows"], g["inner_val"], g["yb"], g["w"]

BASE = 2012 * 12 + 1
M = 192  # months Jan 2012 .. Dec 2027

# ----------------------------------------------------------------------------- locations (building-level coordinates)
allxy = pd.concat([inp[["latitude", "longitude"]], leases[["latitude", "longitude"]]]).dropna().drop_duplicates()
keyf = lambda lat, lng: pd.Series(np.round(np.asarray(lat, float), 5).astype(str)).str.cat(pd.Series(np.round(np.asarray(lng, float), 5).astype(str)), sep=",")
allkeys = keyf(allxy.latitude, allxy.longitude).values
LOC = {k: i for i, k in enumerate(pd.unique(allkeys))}
NLOC = len(LOC)
XY = np.zeros((NLOC, 2))
lat0, cos0 = -33.88, np.cos(np.radians(-33.88))
for k, i in LOC.items():
    la, lo = map(float, k.split(","))
    XY[i] = ((lo - 151.2) * cos0 * 111320.0, (la - lat0) * 110540.0)


def loc_of(lat, lng):
    lat = np.asarray(lat, float); lng = np.asarray(lng, float)
    ok = ~(np.isnan(lat) | np.isnan(lng))
    out = np.full(len(lat), -1)
    out[ok] = keyf(lat[ok], lng[ok]).map(LOC).fillna(-1).astype(int).values
    return out


tree = cKDTree(XY)
NBRS = {}
for r in (250, 500):
    lists = tree.query_ball_point(XY, r)
    NBRS[r] = [np.array([j for j in lst if j != i], dtype=int) for i, lst in enumerate(lists)]
print(f"{NLOC:,} building locations; mean neighbours within 250 m: {np.mean([len(x) for x in NBRS[250]]):.0f}, 500 m: {np.mean([len(x) for x in NBRS[500]]):.0f}")

# ----------------------------------------------------------------------------- normalised pool (rent relative to contemporaneous market)
pool = build.reset_index(drop=True).copy()
pool["loc"] = loc_of(pool.latitude, pool.longitude)
lv0, _ = level(pool, pool, pool.mi + 1, 3)
pool["nrm"] = pool.lr - lv0


def make_ctx(pool):
    b = pool.bedc.values + 1; m = pool.mi.values - BASE; l = pool["loc"].values
    ok = (l >= 0) & (m >= 0) & (m < M)
    S = np.zeros((NLOC, 6, M + 1), dtype=np.float32); N = np.zeros_like(S)
    np.add.at(S, (l[ok], b[ok], m[ok] + 1), pool.nrm.values[ok]); np.add.at(N, (l[ok], b[ok], m[ok] + 1), 1.0)
    S = S.cumsum(axis=2); N = N.cumsum(axis=2)
    return {"S": S, "N": N, "Sa": S.sum(axis=1), "Na": N.sum(axis=1)}


def extras(rows, pool, ctx):
    rows = rows.reset_index(drop=True)
    n = len(rows)
    mi = (rows.listing_date.dt.year * 12 + rows.listing_date.dt.month).reset_index(drop=True)
    lag_end = mi - 3
    out = pd.DataFrame(index=range(n))
    lv = level(pool, rows, lag_end, 3)[0]
    out["mom3"] = lv - level(pool, rows, lag_end - 3, 3)[0]
    out["mom6"] = lv - level(pool, rows, lag_end - 6, 3)[0]
    Sa, Na = window_stats(pool, [], rows, lag_end, 3); Sb_, Nb_ = window_stats(pool, [], rows, lag_end - 6, 3)
    out["mom_city6"] = Sa / np.maximum(Na, 1) - Sb_ / np.maximum(Nb_, 1)
    # the flat's own average premium over the market across ALL its earlier adverts
    ps = pool[["gnaf_id", "listing_date", "nrm"]].sort_values("listing_date").copy()
    ps["cum"] = ps.groupby("gnaf_id").nrm.cumsum(); ps["cnt"] = ps.groupby("gnaf_id").cumcount() + 1
    r2 = rows[["gnaf_id", "listing_date"]].assign(_i=np.arange(n)).sort_values("listing_date")
    mg = pd.merge_asof(r2, ps[["gnaf_id", "listing_date", "cum", "cnt"]], on="listing_date", by="gnaf_id", allow_exact_matches=False).sort_values("_i")
    out["own_nrm"] = (mg.cum / mg.cnt).values; out["own_nrm_n"] = mg.cnt.values
    # building + neighbour premium over the market, 24 months ending 3 months before the target
    loc = loc_of(rows.lat, rows.lng); b = rows.bedc.values + 1
    hi = np.clip(mi.values - 3 - BASE + 1, 0, M); lo = np.clip(mi.values - 3 - 23 - BASE, 0, M)
    valid = loc >= 0
    S, N, SA, NA = ctx["S"], ctx["N"], ctx["Sa"], ctx["Na"]
    cols = {k: np.full(n, np.nan) for k in ["b_same_nrm", "b_same_n", "b_any_nrm", "b_any_n"] + [f"nb{r}_{t}_{u}" for r in (250, 500) for t in ("same", "any") for u in ("nrm", "n")]}
    li = np.where(valid)[0]
    ss = S[loc[li], b[li], hi[li]] - S[loc[li], b[li], lo[li]]; nn = N[loc[li], b[li], hi[li]] - N[loc[li], b[li], lo[li]]
    sa = SA[loc[li], hi[li]] - SA[loc[li], lo[li]]; na = NA[loc[li], hi[li]] - NA[loc[li], lo[li]]
    cols["b_same_n"][li] = nn; cols["b_same_nrm"][li] = np.where(nn > 0, ss / np.maximum(nn, 1), np.nan)
    cols["b_any_n"][li] = na; cols["b_any_nrm"][li] = np.where(na > 0, sa / np.maximum(na, 1), np.nan)
    for l_, idx in pd.Series(np.arange(n)[valid]).groupby(loc[valid]):
        idx = idx.values
        for r in (250, 500):
            nb = NBRS[r][l_]
            if len(nb) == 0:
                for t in ("same", "any"): cols[f"nb{r}_{t}_n"][idx] = 0
                continue
            bb = b[idx][None, :]; h = hi[idx][None, :]; lo_ = lo[idx][None, :]; nbc = nb[:, None]
            s1 = (S[nbc, bb, h] - S[nbc, bb, lo_]).sum(0); n1 = (N[nbc, bb, h] - N[nbc, bb, lo_]).sum(0)
            s2 = (SA[nbc, h] - SA[nbc, lo_]).sum(0); n2 = (NA[nbc, h] - NA[nbc, lo_]).sum(0)
            cols[f"nb{r}_same_n"][idx] = n1; cols[f"nb{r}_same_nrm"][idx] = np.where(n1 > 0, s1 / np.maximum(n1, 1), np.nan)
            cols[f"nb{r}_any_n"][idx] = n2; cols[f"nb{r}_any_nrm"][idx] = np.where(n2 > 0, s2 / np.maximum(n2, 1), np.nan)
    for k, v in cols.items(): out[k] = v
    out["beds_x_baths"] = (rows.bedrooms * rows.bathrooms).values
    out["baths_per_bed"] = (rows.bathrooms / rows.bedrooms.clip(lower=1)).values
    for c in BLOCKF:   # census block features (static; 2026 estimates are allowed)
        out[c] = rows["mb"].map(BLK[c]).values
    out["mb_cat"] = pd.Categorical(rows["mb"].map(BLK["mb_cat"]).values, categories=MB_CATS)
    return out


blocks = pd.read_csv(g["DATA"] / "blocks-homes-and-people-2021-2026.csv").drop_duplicates("mb").set_index("mb")
blocks["people_per_home_2026"] = blocks.people_2026 / blocks.homes_2026.where(blocks.homes_2026 > 0)
blocks["pop_growth"] = (blocks.people_2026 - blocks.people_2021) / blocks.people_2021.where(blocks.people_2021 > 0)
blocks["home_growth"] = (blocks.homes_2026 - blocks.homes_2021) / blocks.homes_2021.where(blocks.homes_2021 > 0)
blocks["new_home_share"] = blocks.new_homes / blocks.homes_2026.where(blocks.homes_2026 > 0)
BLOCKF = ["homes_2021", "homes_2026", "people_2021", "people_2026", "new_homes", "people_per_home_2026", "pop_growth", "home_growth", "new_home_share"]
BLK = blocks
MB_CATS = sorted(blocks.mb_cat.dropna().unique())
EXTRA = ["mom3", "mom6", "mom_city6", "own_nrm", "own_nrm_n", "b_same_nrm", "b_same_n", "b_any_nrm", "b_any_n"] + [f"nb{r}_{t}_{u}" for r in (250, 500) for t in ("same", "any") for u in ("nrm", "n")] + ["beds_x_baths", "baths_per_bed"]
FEATS2 = FEATS1 + EXTRA
FEATS3 = FEATS2 + BLOCKF + ["mb_cat"]
ctx = make_ctx(pool)
Xb2 = pd.concat([Xb1.reset_index(drop=True), extras(tr_rows.assign(lat=tr_rows.lat), pool, ctx)], axis=1)
print("v2 feature matrix:", Xb2.shape, "| share of rows with building premium:", round(float(Xb2.b_any_nrm.notna().mean()), 3), "| neighbour(250m) premium:", round(float(Xb2.nb250_same_nrm.notna().mean()), 3))

# ----------------------------------------------------------------------------- variants compared on the inner slice
iv = inner_val
yv = build.weekly_rent.values


def fit(X, y, wt, tr_mask, va_mask, resid):
    off = X.level_lag.values if resid else 0.0
    tgt = y - off
    m = lgb.train(params, lgb.Dataset(X[tr_mask], tgt[tr_mask] if resid else tgt[tr_mask], weight=wt[tr_mask]), num_boost_round=3000,
                  valid_sets=[lgb.Dataset(X[va_mask], tgt[va_mask])], callbacks=[lgb.early_stopping(100, verbose=False)])
    return m


def predict(m, X, resid):
    return np.exp(m.predict(X) + (X.level_lag.values if resid else 0.0))


variants = {"A_v1_direct": (Xb2[FEATS1], False), "B_v2_direct": (Xb2[FEATS2], False), "C_v2_residual": (Xb2[FEATS2], True),
            "D_v3_blocks_direct": (Xb2[FEATS3], False), "E_v3_blocks_residual": (Xb2[FEATS3], True)}
inner = {}
for name, (X, resid) in variants.items():
    m = fit(X, np.log(yv) if False else yb, w, ~iv, iv, resid)
    p = predict(m, X[iv], resid)
    inner[name] = (m, score(yv[iv], p))
    print(f"{name:16s} inner: {{ med_err ${inner[name][1]['median_abs_error']:.1f}, within100 {inner[name][1]['within_100']:.3f}, r2 {inner[name][1]['r2']:.3f} }}  iters {m.best_iteration}")
best_name = min(inner, key=lambda k: inner[k][1]["median_abs_error"])
print("best variant on inner slice:", best_name)
Xbest, resid = variants[best_name]
m_inner = inner[best_name][0]

# drift correction: fit on April rows of the inner slice, test on May rows
pv = predict(m_inner, Xbest[iv], resid); dv = build[iv].listing_date.dt.month.values
apr, may = dv == 4, dv == 5
c_apr = float(np.median(np.log(yv[iv][apr] / pv[apr])))
no_c = score(yv[iv][may], pv[may]); with_c = score(yv[iv][may], pv[may] * np.exp(c_apr))
print(f"drift correction fitted on April (log {c_apr:+.4f}); May rows: without ${no_c['median_abs_error']:.1f} / with ${with_c['median_abs_error']:.1f}")
use_c = with_c["median_abs_error"] < no_c["median_abs_error"]
c_final = float(np.median(np.log(yv[iv] / pv))) if use_c else 0.0
print("using drift correction:", use_c, f"(final log correction {c_final:+.4f})")

# ----------------------------------------------------------------------------- final fit on the whole build pile
best_iter = int(m_inner.best_iteration * 1.05)
off = Xbest.level_lag.values if resid else 0.0
final_model = lgb.train(params, lgb.Dataset(Xbest, yb - off, weight=w), num_boost_round=best_iter)
BEST_FEATS = list(Xbest.columns)
imp = pd.Series(final_model.feature_importance("gain"), index=BEST_FEATS).sort_values(ascending=False)
print("top features by gain:", (imp / imp.sum()).round(3).head(10).to_dict())

# check pile: scored ONCE
ck = rows_from_leases(scored.drop(columns=[c for c in scored.columns if c.endswith("_s")], errors="ignore")).assign(car=scored.car_state.values)
Xc = pd.concat([build_features(ck, build).reset_index(drop=True), extras(ck, pool, ctx)], axis=1)
Xc_use = Xc[BEST_FEATS]
pc = predict(final_model, Xc_use, resid) * np.exp(c_final)
m_v2 = score(scored.weekly_rent.values, pc)
print("v2 on the check pile (scored once):", {k: round(v, 3) for k, v in m_v2.items()})
print("v1 on the check pile                :", {k: round(v, 3) for k, v in m_lgb_v1.items()})

# final predictions for all flats
fin = inp.rename(columns={"latitude": "lat", "longitude": "lng"}).copy(); fin["listing_date"] = PRED_DATE
ex_fin = extras(fin, pool, ctx)
preds = {}
for name, car in [("without", 0.0), ("with", 1.0)]:
    Xf = pd.concat([build_features(fin.assign(car=car), build).reset_index(drop=True), ex_fin], axis=1)
    preds[name] = predict(final_model, Xf[BEST_FEATS], resid) * np.exp(c_final)
v2 = pd.DataFrame({"gnaf_id": inp.gnaf_id, "rent_with_car_space": np.round(np.maximum(preds["with"], preds["without"])), "rent_without_car_space": np.round(preds["without"])})
bad = ~np.isfinite(v2[["rent_with_car_space", "rent_without_car_space"]]).all(axis=1) | (v2.rent_without_car_space <= 0)
v2.loc[bad, ["rent_with_car_space", "rent_without_car_space"]] = safety.loc[bad, ["rent_with_car_space", "rent_without_car_space"]].values
v2.to_csv(OUT / "lightgbm_v2.csv", index=False)
print("rows replaced by the baseline fallback:", int(bad.sum()))

prem = v2.rent_with_car_space - v2.rent_without_car_space
print(f"v2 car premium $/wk: median {prem.median():.0f}, p10 {prem.quantile(.1):.0f}, p90 {prem.quantile(.9):.0f}")
PREV_V2_MED = 44.09   # previous promoted v2 (momentum + neighbour features) on the check pile
promote = m_v2["median_abs_error"] <= PREV_V2_MED
if promote:
    f = v2.copy()
    for c in ["rent_with_car_space", "rent_without_car_space"]: f[c] = f[c].fillna(safety[c])
    assert len(f) == 65_777 and f.gnaf_id.is_unique and set(f.gnaf_id) == set(inp.gnaf_id) and f.notna().all().all()
    assert (f.rent_without_car_space > 0).all() and (f.rent_with_car_space >= f.rent_without_car_space).all()
    f.to_csv(OUT / "rents_d4data.csv", index=False)
print("PROMOTED v2 to rents_d4data.csv" if promote else "v2 did not beat v1 on the check pile: rents_d4data.csv unchanged (still v1)")
metrics = json.load(open(OUT / "metrics.json"))
metrics.update({"lightgbm_v2": m_v2, "v2_variant": best_name, "v2_drift_correction_log": c_final, "v2_inner_slice": {k: v[1] for k, v in inner.items()}, "winner": "lightgbm_v2" if promote else metrics.get("winner")})
json.dump(metrics, open(OUT / "metrics.json", "w"), indent=2)
