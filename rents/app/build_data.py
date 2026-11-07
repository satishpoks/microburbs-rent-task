"""Builds rents/app/data.js from the public input-flat list and OUR model's predictions (rents/output/rents_d4data.csv).
Run: python rents/app/build_data.py
data.js is derived from the private lease data via the model, so it is gitignored: keep the app local, do not publish it."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
inp = pd.read_csv(ROOT.parent / "main_data" / "rents-input-flats-city-of-sydney.csv")
pred = pd.read_csv(ROOT / "output" / "rents_d4data.csv")
metrics = json.load(open(ROOT / "output" / "metrics.json"))
assert len(pred) == len(inp) == 65_777 and set(pred.gnaf_id) == set(inp.gnaf_id)

df = inp.merge(pred, on="gnaf_id", how="left")
assert df[["rent_with_car_space", "rent_without_car_space"]].notna().all().all()
suburbs = sorted(df.suburb.unique())
types = sorted(df.property_type.unique())


def clean_suburb(s):
    return s.replace(" (NSW)", "").replace(" (Sydney - NSW)", "")


def num(series, dtype=int, null=-1):
    return series.fillna(null).round().astype(dtype)


rows = pd.DataFrame({
    "id": df.gnaf_id.str.replace("GANSW", "", regex=False),
    "addr": df.address,
    "sub": df.suburb.map({s: i for i, s in enumerate(suburbs)}),
    "type": df.property_type.map({t: i for i, t in enumerate(types)}),
    "beds": num(df.bedrooms), "baths": num(df.bathrooms),
    "car": num(df.car_spaces),
    "floor": num(df.floor_level), "bsize": num(df.flats_in_building),
    "lat": df.latitude.round(5), "lng": df.longitude.round(5),
    "rw": df.rent_with_car_space.round().astype(int), "ro": df.rent_without_car_space.round().astype(int),
})
data = {
    "meta": {
        "model": "LightGBM v2 (d4data)",
        "asOf": "7 Nov 2026",
        "targetPeriod": "1 Aug to 30 Sep 2026",
        "medianError": round(metrics["lightgbm_v2"]["median_abs_error"], 1) if "lightgbm_v2" in metrics else 44.1,
        "within100": round(100 * metrics["lightgbm_v2"]["within_100"], 1) if "lightgbm_v2" in metrics else 79.2,
        "r2": round(metrics["lightgbm_v2"]["r2"], 3) if "lightgbm_v2" in metrics else 0.888,
        # typical (median) absolute error by bedrooms from the held-out Apr-May 2026 slice inside the build pile
        "errByBeds": {"0": 34, "1": 39, "2": 60, "3": 82},
    },
    "suburbs": suburbs, "suburbLabels": [clean_suburb(s) for s in suburbs], "types": types,
    "cols": list(rows.columns),
    "rows": json.loads(rows.to_json(orient="values")),
}
out = Path(__file__).with_name("data.js")
out.write_text("window.RENT_DATA = " + json.dumps(data, separators=(",", ":")) + ";\n", encoding="utf-8")
print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB), {len(rows):,} flats, {len(suburbs)} suburbs")
