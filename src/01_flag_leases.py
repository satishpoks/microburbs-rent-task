"""Step 1: flag suspicious rows in the supplied past-leases file (the raw file is never edited).

Reads  data/rents-past-leases-city-of-sydney.csv  (supplied, private)
Writes data/leases_flagged.csv                    (same rows + 8 flag columns + `drop_candidate`)

Hard flags (a row with any of them is dropped before modelling): impossible bedroom/bathroom counts,
rent far from the median of its suburb x bedrooms x year, and exact duplicate rows.
Soft flags are kept for information only. No date cutoff is applied here; later steps cut at 31 Jul 2026.

Run: python src/01_flag_leases.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

D = Path(__file__).resolve().parents[1] / "data"
pl = pd.read_csv(D / "rents-past-leases-city-of-sydney.csv", parse_dates=["listing_date"])

fl = pl.copy()
fl['year'] = fl.listing_date.dt.year
bed = fl.bedrooms.fillna(1)
fl['bad_beds'] = (fl.bedrooms >= 6) | ((fl.bedrooms % 1) != 0)
fl['bad_baths'] = (fl.bathrooms >= 5) | (fl.bathrooms == 0)
fl['inconsistent'] = ((fl.bathrooms - bed) >= 3) | ((fl.bedrooms == 0) & (fl.bathrooms >= 2))

# rent extreme: robust z-score and ratio vs median of suburb x bedrooms x year (fallback bedrooms x year if group < 8)
fl['lr'] = np.log(fl.weekly_rent)
fl['bedc'] = fl.bedrooms.clip(upper=4).fillna(-1)
def grp_stats(keys):
    med = fl.groupby(keys).lr.transform('median')
    mad = (fl.lr - med).abs().groupby([fl[k] for k in keys]).transform('median')
    n = fl.groupby(keys).lr.transform('size')
    return med, mad, n
m1, d1, n1 = grp_stats(['suburb', 'bedc', 'year']); m2, d2, n2 = grp_stats(['bedc', 'year'])
use1 = n1 >= 8
med = m1.where(use1, m2); mad = d1.where(use1, d2).clip(lower=0.05)
fl['z'] = 0.6745 * (fl.lr - med) / mad
fl['ratio'] = np.exp(fl.lr - med)
fl['rent_extreme'] = (fl.z.abs() > 5) | (fl.ratio > 3) | (fl.ratio < 1/3)

fl['rpb'] = fl.weekly_rent / fl.bedrooms.clip(lower=1)
lo, hi = fl.rpb.quantile([.005, .995])
fl['rent_per_bed_odd'] = (fl.rpb < lo) | (fl.rpb > hi)

exact = fl.duplicated(subset=['gnaf_id', 'listing_date', 'weekly_rent', 'bedrooms', 'bathrooms', 'car_space', 'address'], keep='first')
same_day = fl.duplicated(subset=['gnaf_id', 'listing_date'], keep=False) & ~exact
fl['dup_row'] = exact
fl['same_day_diff_rent'] = same_day

s_ = fl.sort_values(['gnaf_id', 'listing_date'])
prev = s_.groupby('gnaf_id').lr.shift()
fl['price_jump'] = ((s_.lr - prev).abs() > np.log(2)).reindex(fl.index).fillna(False)

FLAGS = ['bad_beds', 'bad_baths', 'inconsistent', 'rent_extreme', 'rent_per_bed_odd', 'dup_row', 'same_day_diff_rent', 'price_jump']
HARD = ['bad_beds', 'bad_baths', 'inconsistent', 'rent_extreme', 'dup_row']
fl['drop_candidate'] = fl[HARD].any(axis=1)
print(pd.DataFrame({'rows': fl[FLAGS].sum(), 'pct': (fl[FLAGS].mean() * 100).round(2)}).to_string())
print('rows with any hard flag (dropped before modelling):', fl.drop_candidate.sum(), f'({fl.drop_candidate.mean():.2%})')

keep_cols = [c_ for c_ in pl.columns if c_ not in ('year', 'ym', 'q', 'regime')] + FLAGS + ['drop_candidate']
out = D / "leases_flagged.csv"
fl[keep_cols].to_csv(out, index=False)
print('saved', out, fl.shape[0], 'rows')
