"""Baseline + LightGBM v1 for the rent task.

Run:  python rents/baseline.py
Reads ../main_data (private, gitignored). Writes rents/output/*.csv and metrics.json.

Rules respected: only adverts dated <= 2026-07-31; build pile = adverts before 1 Jun 2026; check pile = 1 Jun-31 Jul 2026 is touched once
for scoring and never used for fitting or tuning (early stopping uses Apr-May 2026 INSIDE the build pile). Final predictions are fitted on the
build pile only (retraining on the check pile is an open question for the organisers).
"""
import json
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT.parent / "main_data"
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)

BUILD_END = pd.Timestamp("2026-06-01")      # build pile: strictly before this
CHECK_END = pd.Timestamp("2026-07-31")      # nothing later than this is ever used
PRED_DATE = pd.Timestamp("2026-08-15")      # centre of the scored Aug-Sep window
EXPECTED_ROWS = 65_777
MIN_N = 5

inp = pd.read_csv(DATA / "rents-input-flats-city-of-sydney.csv")
leases = pd.read_csv(DATA / "leases_flagged.csv", parse_dates=["listing_date"])   # made by main_data/01_eda.ipynb (flags only; raw file untouched)
assert len(inp) == EXPECTED_ROWS and inp.gnaf_id.is_unique

leases = leases[(leases.listing_date <= CHECK_END) & leases.weekly_rent.notna() & ~leases.drop_candidate].copy()
leases["lr"] = np.log(leases.weekly_rent)
leases["bedc"] = leases.bedrooms.clip(upper=4).fillna(-1).astype(int)
leases["mi"] = leases.listing_date.dt.year * 12 + leases.listing_date.dt.month
build = leases[leases.listing_date < BUILD_END].copy()
check = leases[leases.listing_date >= BUILD_END].copy()
print(f"build adverts {len(build):,} | check adverts {len(check):,} (never fitted on)")

inp["bedc"] = inp.bedrooms.clip(upper=4).fillna(-1).astype(int)
inp["car_in"] = inp.car_spaces.where(inp.car_spaces.notna(), inp.car_space)

# --------------------------------------------------------------------------------------- scoring
def score(y, p):
    e = np.abs(y - p)
    ss_res = ((y - p) ** 2).sum(); ss_tot = ((y - y.mean()) ** 2).sum()
    return {"median_abs_error": float(np.median(e)), "within_100": float((e <= 100).mean()), "r2": float(1 - ss_res / ss_tot), "n": int(len(y))}


def advert_car_state(df):
    """Parking state used for scoring an advert: its own, else the input flat's, else unknown."""
    c = df.car_space.copy()
    c = c.where(c.notna(), df.car_in)
    return (c > 0).astype(float).where(c.notna())


# --------------------------------------------------------------------------------------- 1. median baseline
LEVELS = [["suburb", "bedc", "bathc", "car"], ["suburb", "bedc", "car"], ["bedc", "car"], ["car"]]


def median_chain(train, test):
    t = train.assign(bathc=train.bathrooms.clip(upper=3).fillna(-1).astype(int), car=(train.car_space > 0).astype(float).where(train.car_space.notna()))
    t = t[t.car.notna()]
    q = test.assign(bathc=test.bathc)
    pred = pd.Series(np.nan, index=q.index)
    for keys in LEVELS:
        g = t.groupby(keys).weekly_rent.agg(med="median", n="size").reset_index()
        g = g[g.n >= MIN_N]
        m = q[keys].reset_index().merge(g, on=keys, how="left").set_index("index")
        pred = pred.fillna(m.med)
    return pred.fillna(t.weekly_rent.median())


def baseline_predict(train, rows):
    """rows has suburb, bedc, bathc; returns with/without car predictions."""
    recent = train[train.listing_date >= BUILD_END - pd.DateOffset(months=12)]
    out = {}
    for name, car in [("without", 0.0), ("with", 1.0)]:
        out[name] = median_chain(recent, rows.assign(car=car))
    out["with"] = np.maximum(out["with"], out["without"])
    return out


inp["bathc"] = inp.bathrooms.clip(upper=3).fillna(-1).astype(int)
check = check.merge(inp[["gnaf_id", "car_space", "car_spaces", "building_address", "floor_level", "flats_in_building", "block_homes_2026", "block_new_homes_2021_2026"]]
                    .rename(columns={"car_space": "car_in_a", "building_address": "bld_in"}), on="gnaf_id", how="left")
check["car_in"] = check.car_spaces.where(check.car_spaces.notna(), check.car_in_a)
check["bathc"] = check.bathrooms.clip(upper=3).fillna(-1).astype(int)
check["car_state"] = advert_car_state(check)
scored = check[check.car_state.notna()].copy()
print(f"check adverts with a known parking state: {len(scored):,} of {len(check):,}")

bp = baseline_predict(build, scored)
scored["p_base"] = np.where(scored.car_state == 1, bp["with"], bp["without"])
m_base = score(scored.weekly_rent.values, scored.p_base.values)
print("median-chain baseline on the check pile:", {k: round(v, 3) for k, v in m_base.items()})

# safety CSV from the baseline
bi = baseline_predict(build, inp)
safety = pd.DataFrame({"gnaf_id": inp.gnaf_id, "rent_with_car_space": bi["with"].round(0), "rent_without_car_space": bi["without"].round(0)})
safety.to_csv(OUT / "baseline_median.csv", index=False)


# --------------------------------------------------------------------------------------- 2. LightGBM
def window_stats(pool, keys, rows, mi_end, win):
    g = pool.groupby(keys + ["mi"]).lr.agg(S="sum", N="count").reset_index()
    S = np.zeros(len(rows)); N = np.zeros(len(rows))
    for o in range(win):
        q = rows[keys].copy() if keys else pd.DataFrame(index=rows.index)
        q["mi"] = (mi_end - o).values
        m = q.merge(g, on=keys + ["mi"], how="left")
        S += m.S.fillna(0).values; N += m.N.fillna(0).values
    return S, N


def level(pool, rows, mi_end, win=3, k=5):
    S1, N1 = window_stats(pool, ["suburb", "bedc"], rows, mi_end, win)
    S2, N2 = window_stats(pool, ["bedc"], rows, mi_end, win)
    S3, N3 = window_stats(pool, [], rows, mi_end, win)
    mean2 = np.where(N2 > 0, S2 / np.maximum(N2, 1), S3 / np.maximum(N3, 1))
    return (S1 + k * mean2) / (N1 + k), N1


def build_features(rows, pool):
    """rows: one row per prediction with gnaf_id, listing_date (target date), suburb, bedc, car (0/1/NaN), static attrs.
    All time-varying features use only `pool` and are lagged 3 months (mimics Aug-Sep targets with data ending May)."""
    rows = rows.reset_index(drop=True).copy()
    rows["mi"] = rows.listing_date.dt.year * 12 + rows.listing_date.dt.month
    lag_end = rows.mi - 3
    rows["level_lag"], rows["level_n"] = level(pool, rows, lag_end, 3)
    # own history: latest pool advert strictly before the target date
    ps = pool[["gnaf_id", "listing_date", "lr"]].sort_values(["listing_date"]).copy()
    ps["prev_cnt"] = ps.groupby("gnaf_id").cumcount() + 1
    ps = ps.rename(columns={"listing_date": "prev_date", "lr": "prev_lr"}); ps["listing_date"] = ps.prev_date
    r2 = rows[["gnaf_id", "listing_date"]].assign(_i=np.arange(len(rows))).sort_values("listing_date")
    mg = pd.merge_asof(r2, ps, on="listing_date", by="gnaf_id", direction="backward", allow_exact_matches=False).sort_values("_i")
    rows["prev_lr"] = mg.prev_lr.values; rows["prev_cnt"] = mg.prev_cnt.values
    rows["prev_gap"] = (rows.listing_date - mg.prev_date).dt.days.values
    has = rows.prev_lr.notna().values
    pm = (mg.prev_date.dt.year * 12 + mg.prev_date.dt.month).values
    lv_prev = np.full(len(rows), np.nan)
    if has.any():
        sub = rows[has]
        lv_prev[has] = level(pool, sub, pd.Series(pm[has] - 3, index=sub.index), 3)[0]
    rows["level_prev"] = lv_prev
    rows["growth_est"] = rows.level_lag - rows.level_prev
    rows["adj_prev"] = rows.prev_lr + rows.growth_est
    # building context over the 12 months ending 3 months before
    Sb, Nb = window_stats(pool, ["building_address", "bedc"], rows, lag_end, 12)
    Ss, Ns = window_stats(pool, ["suburb", "bedc"], rows, lag_end, 12)
    rows["bldg_n"] = Nb
    rows["bldg_rel"] = np.where((Nb > 0) & (Ns > 0), Sb / np.maximum(Nb, 1) - Ss / np.maximum(Ns, 1), np.nan)
    rows["suburb"] = pd.Categorical(rows.suburb, categories=SUBURBS)
    rows["prop"] = pd.Categorical(rows.property_type, categories=PROPS)
    return rows[FEATS]


SUBURBS = sorted(inp.suburb.unique()); PROPS = sorted(inp.property_type.unique())
FEATS = ["bedrooms", "bathrooms", "car", "prop", "suburb", "lat", "lng", "floor_level", "flats_in_building", "block_homes_2026", "block_new_homes_2021_2026",
         "level_lag", "level_n", "prev_lr", "prev_cnt", "prev_gap", "level_prev", "growth_est", "adj_prev", "bldg_n", "bldg_rel"]
static = inp.set_index("gnaf_id")[["floor_level", "flats_in_building", "block_homes_2026", "block_new_homes_2021_2026", "building_address", "latitude", "longitude"]]


def rows_from_leases(df):
    r = df.merge(static.rename(columns={"building_address": "bld_in2"}), left_on="gnaf_id", right_index=True, how="left", suffixes=("", "_s"))
    for c in ["floor_level", "flats_in_building", "block_homes_2026", "block_new_homes_2021_2026"]:
        if c + "_s" in r.columns: r[c] = r[c + "_s"]
    r["building_address"] = r.building_address.where(r.building_address.notna(), r.get("bld_in2"))
    r["car"] = (r.car_space > 0).astype(float).where(r.car_space.notna())
    r["lat"] = r.latitude; r["lng"] = r.longitude
    return r


tr_rows = rows_from_leases(build)
Xb = build_features(tr_rows, build)
yb = build.lr.values
age = (BUILD_END - build.listing_date).dt.days.values / 365.25
w = 0.5 ** (age / 3.0)
inner_val = (build.listing_date >= "2026-04-01").values
params = dict(objective="l1", learning_rate=0.05, num_leaves=63, min_child_samples=40, feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1, verbose=-1, seed=7)
m_inner = lgb.train(params, lgb.Dataset(Xb[~inner_val], yb[~inner_val], weight=w[~inner_val]), num_boost_round=3000,
                    valid_sets=[lgb.Dataset(Xb[inner_val], yb[inner_val])], callbacks=[lgb.early_stopping(100, verbose=False)])
best = int(m_inner.best_iteration * 1.05)
print("inner early stopping (Apr-May 2026 inside the build pile): best iterations", m_inner.best_iteration)
model = lgb.train(params, lgb.Dataset(Xb, yb, weight=w), num_boost_round=best)

# check-pile score, touched once
ck_rows = rows_from_leases(scored.drop(columns=[c for c in scored.columns if c.endswith("_s")], errors="ignore"))
Xc = build_features(ck_rows.assign(car=scored.car_state.values), build)
scored["p_lgb"] = np.exp(model.predict(Xc))
m_lgb = score(scored.weekly_rent.values, scored.p_lgb.values)
print("LightGBM v1 on the check pile:", {k: round(v, 3) for k, v in m_lgb.items()})
imp = pd.Series(model.feature_importance("gain"), index=FEATS).sort_values(ascending=False)
print("top features by gain:", (imp / imp.sum()).round(3).head(8).to_dict())

# final predictions for all flats
fin = inp.rename(columns={"latitude": "lat", "longitude": "lng", "property_type": "property_type"}).copy()
fin["listing_date"] = PRED_DATE
preds = {}
for name, car in [("without", 0.0), ("with", 1.0)]:
    Xf = build_features(fin.assign(car=car), build)
    preds[name] = np.exp(model.predict(Xf))
lgb_with = np.maximum(preds["with"], preds["without"])
lgb_df = pd.DataFrame({"gnaf_id": inp.gnaf_id, "rent_with_car_space": np.round(lgb_with), "rent_without_car_space": np.round(preds["without"])})
# fallback to the baseline wherever the model gave a non-finite / non-positive value
bad = ~np.isfinite(lgb_df[["rent_with_car_space", "rent_without_car_space"]]).all(axis=1) | (lgb_df.rent_without_car_space <= 0)
lgb_df.loc[bad, ["rent_with_car_space", "rent_without_car_space"]] = safety.loc[bad, ["rent_with_car_space", "rent_without_car_space"]].values
lgb_df.to_csv(OUT / "lightgbm_v1.csv", index=False)

# --------------------------------------------------------------------------------------- choose + validate submission file
winner = "lightgbm_v1" if m_lgb["median_abs_error"] < m_base["median_abs_error"] else "baseline_median"
sub = lgb_df if winner == "lightgbm_v1" else safety
final = sub.copy()
for c in ["rent_with_car_space", "rent_without_car_space"]:
    final[c] = final[c].fillna(safety[c]).fillna(float(build.weekly_rent.median()))
assert len(final) == EXPECTED_ROWS and final.gnaf_id.is_unique and set(final.gnaf_id) == set(inp.gnaf_id)
assert final[["rent_with_car_space", "rent_without_car_space"]].notna().all().all() and (final.rent_without_car_space > 0).all()
assert (final.rent_with_car_space >= final.rent_without_car_space).all()
final.to_csv(OUT / "rents_d4data.csv", index=False)
prem = (final.rent_with_car_space - final.rent_without_car_space)
print(f"WROTE {OUT / 'rents_d4data.csv'} from {winner}; car premium $/wk median {prem.median():.0f}, p10 {prem.quantile(.1):.0f}, p90 {prem.quantile(.9):.0f}")
json.dump({"build_end": str(BUILD_END.date()), "check_window": "2026-06-01..2026-07-31", "n_build": len(build), "n_check_scored": len(scored), "baseline_median": m_base,
           "lightgbm_v1": m_lgb, "winner": winner, "organiser_baseline": {"median_abs_error": 86, "within_100": 0.5521}}, open(OUT / "metrics.json", "w"), indent=2)
