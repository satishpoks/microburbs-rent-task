"""Are neighbour / building features impactful, and would block-level or very-near (100 m) neighbours add more?
All scoring is on the INNER slice (Apr-May 2026, inside the build pile); the check pile is not touched; nothing is written to the submission.
Run: python src/experiments/neighbour_ablation.py   (re-runs model_v2.py first, ~4 min, then ~12 small fits)"""
import runpy
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

g = runpy.run_path(str(Path(__file__).resolve().parents[1] / "03_model_v2.py"))
Xb2, build, tr_rows, pool, iv, yb, w, params, yv = g["Xb2"], g["build"], g["tr_rows"], g["pool"], g["iv"], g["yb"], g["w"], g["params"], g["yv"]
XY, tree, loc_of, BASE, M, NLOC, inp, leases, score = g["XY"], g["tree"], g["loc_of"], g["BASE"], g["M"], g["NLOC"], g["inp"], g["leases"], g["score"]
FEATS1, EXTRA = g["FEATS1"], g["EXTRA"]
pd.set_option("display.width", 200)

# ----------------------------------------------------------------- new feature families: 100 m neighbours and mesh-block premium
mi = (tr_rows.listing_date.dt.year * 12 + tr_rows.listing_date.dt.month).reset_index(drop=True).values
b = tr_rows.bedc.values + 1
hi = np.clip(mi - 3 - BASE + 1, 0, M); lo = np.clip(mi - 3 - 23 - BASE, 0, M)
n = len(tr_rows)


def make_arrays(ids, nkeys):
    bb = pool.bedc.values + 1; m = pool.mi.values - BASE
    ok = (ids >= 0) & (m >= 0) & (m < M)
    S = np.zeros((nkeys, 6, M + 1), dtype=np.float32); N = np.zeros_like(S)
    np.add.at(S, (ids[ok], bb[ok], m[ok] + 1), pool.nrm.values[ok]); np.add.at(N, (ids[ok], bb[ok], m[ok] + 1), 1.0)
    S = S.cumsum(axis=2); N = N.cumsum(axis=2)
    return S, N, S.sum(axis=1), N.sum(axis=1)


# mesh block (census block) premium over the market, 24 months ending 3 months before
allmb = pd.unique(pd.concat([inp.mb, leases.mb]).dropna())
MBID = {k: i for i, k in enumerate(allmb)}
mb_pool = pool.mb.map(MBID).fillna(-1).astype(int).values; mb_rows = tr_rows.mb.map(MBID).fillna(-1).astype(int).values
S, N, SA, NA = make_arrays(mb_pool, len(MBID))
f = {k: np.full(n, np.nan) for k in ["mb_same_nrm", "mb_same_n", "mb_any_nrm", "mb_any_n"]}
v = np.where(mb_rows >= 0)[0]
ss = S[mb_rows[v], b[v], hi[v]] - S[mb_rows[v], b[v], lo[v]]; nn = N[mb_rows[v], b[v], hi[v]] - N[mb_rows[v], b[v], lo[v]]
sa = SA[mb_rows[v], hi[v]] - SA[mb_rows[v], lo[v]]; na = NA[mb_rows[v], hi[v]] - NA[mb_rows[v], lo[v]]
f["mb_same_n"][v] = nn; f["mb_same_nrm"][v] = np.where(nn > 0, ss / np.maximum(nn, 1), np.nan)
f["mb_any_n"][v] = na; f["mb_any_nrm"][v] = np.where(na > 0, sa / np.maximum(na, 1), np.nan)

# very-near neighbours: other buildings within 100 m
loc_pool = pool["loc"].values; loc_rows = loc_of(tr_rows.lat, tr_rows.lng)
S, N, SA, NA = make_arrays(loc_pool, NLOC)
NB100 = [np.array([j for j in lst if j != i], dtype=int) for i, lst in enumerate(tree.query_ball_point(XY, 100))]
for k in ["nb100_same_nrm", "nb100_same_n", "nb100_any_nrm", "nb100_any_n"]: f[k] = np.full(n, np.nan)
for l_, idx in pd.Series(np.arange(n)[loc_rows >= 0]).groupby(loc_rows[loc_rows >= 0]):
    idx = idx.values; nb = NB100[l_]
    if len(nb) == 0:
        f["nb100_same_n"][idx] = 0; f["nb100_any_n"][idx] = 0; continue
    bb = b[idx][None, :]; h = hi[idx][None, :]; lo_ = lo[idx][None, :]; nbc = nb[:, None]
    s1 = (S[nbc, bb, h] - S[nbc, bb, lo_]).sum(0); n1 = (N[nbc, bb, h] - N[nbc, bb, lo_]).sum(0)
    s2 = (SA[nbc, h] - SA[nbc, lo_]).sum(0); n2 = (NA[nbc, h] - NA[nbc, lo_]).sum(0)
    f["nb100_same_n"][idx] = n1; f["nb100_same_nrm"][idx] = np.where(n1 > 0, s1 / np.maximum(n1, 1), np.nan)
    f["nb100_any_n"][idx] = n2; f["nb100_any_nrm"][idx] = np.where(n2 > 0, s2 / np.maximum(n2, 1), np.nan)
X = Xb2.copy()
for k, v_ in f.items(): X[k] = v_

# ----------------------------------------------------------------- feature sets
OWN = ["mom3", "mom6", "mom_city6", "own_nrm", "own_nrm_n", "beds_x_baths", "baths_per_bed"]
BLD = ["b_same_nrm", "b_same_n", "b_any_nrm", "b_any_n"]
NB = [f"nb{r}_{t}_{u}" for r in (250, 500) for t in ("same", "any") for u in ("nrm", "n")]
MB = ["mb_same_nrm", "mb_same_n", "mb_any_nrm", "mb_any_n"]
NB100F = ["nb100_same_nrm", "nb100_same_n", "nb100_any_nrm", "nb100_any_n"]
SETS = {
    "0 v1 features (no momentum/own/spatial)": FEATS1,
    "1 + momentum & own premium (no spatial)": FEATS1 + OWN,
    "2 + same-building premium": FEATS1 + OWN + BLD,
    "3 + 250/500 m neighbours  (= submitted v2)": FEATS1 + OWN + BLD + NB,
    "4 neighbours only (no building)": FEATS1 + OWN + NB,
    "5 v2 + 100 m neighbours": FEATS1 + OWN + BLD + NB + NB100F,
    "6 v2 + mesh-block premium": FEATS1 + OWN + BLD + NB + MB,
    "7 v2 + 100 m + mesh-block": FEATS1 + OWN + BLD + NB + NB100F + MB,
}
hist = X.prev_lr.notna().values[iv]; bld0 = (X.bldg_n.values[iv] == 0)
rows = []
for name, cols in SETS.items():
    res = []
    for sd in (7, 11):
        m = lgb.train({**params, "seed": sd}, lgb.Dataset(X[cols][~iv], yb[~iv], weight=w[~iv]), num_boost_round=3000,
                      valid_sets=[lgb.Dataset(X[cols][iv], yb[iv])], callbacks=[lgb.early_stopping(100, verbose=False)])
        p = np.exp(m.predict(X[cols][iv])); e = np.abs(p - yv[iv])
        res.append([np.median(e), (e <= 100).mean(), score(yv[iv], p)["r2"], np.median(e[~hist]), np.median(e[bld0]), np.median(e[hist & ~bld0])])
    r = np.mean(res, axis=0)
    rows.append({"feature set": name, "n_feats": len(cols), "median_err": r[0], "within_100": r[1], "r2": r[2], "no-history flats": r[3], "bldg w/o recent same-bed ads": r[4], "has history+building data": r[5]})
    print(f"done {name}", flush=True)
out = pd.DataFrame(rows).set_index("feature set")
print("\nINNER SLICE (mean of 2 seeds), $ median abs error unless stated:")
print(out.round(3).to_string())
