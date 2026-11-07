"""Extra report sections: most contributing factors, data sources, how the momentum factor is calculated. Imported by build_report.py."""
import json
from html import escape
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
F = pd.read_csv(ROOT / "results" / "feature_impact.csv", index_col=0)
F.columns = ["gain", "shap", "logpts", "swing"]
ME = json.load(open(ROOT / "results" / "momentum_example.json"))

NAMES = {
    "level_lag": "Recent market rent for the flat's suburb and bedrooms", "adj_prev": "The flat's own last rent, grown by the market since",
    "b_any_nrm": "The building's premium over the market (all bedroom counts)", "prev_lr": "The flat's own last advertised rent", "prop": "Property type",
    "bathrooms": "Bathrooms", "mom_city6": "City-wide 6-month market momentum", "bldg_rel": "Building rent gap vs its suburb (12 months)", "car": "Car space",
    "own_nrm": "The flat's average premium over the market", "b_same_nrm": "The building's premium (same bedroom count)", "suburb": "Suburb",
}
GROUPS = {
    "Market level and momentum": ["level_lag", "level_n", "mom3", "mom6", "mom_city6", "growth_est", "level_prev"],
    "The flat's own rent history": ["prev_lr", "adj_prev", "prev_gap", "prev_cnt", "own_nrm", "own_nrm_n"],
    "Building premium": ["bldg_rel", "bldg_n", "b_same_nrm", "b_same_n", "b_any_nrm", "b_any_n"],
    "Flat size and type": ["bedrooms", "bathrooms", "beds_x_baths", "baths_per_bed", "prop"],
    "Neighbourhood premium (250 m, 500 m)": [i for i in F.index if i.startswith("nb")],
    "Parking": ["car"], "Suburb and coordinates": ["suburb", "lat", "lng"],
    "Building and block context": ["floor_level", "flats_in_building", "block_homes_2026", "block_new_homes_2021_2026"],
}
grp = sorted(((k, float(F.loc[[i for i in v if i in F.index], "shap"].sum())) for k, v in GROUPS.items()), key=lambda t: -t[1])


def groups_svg():
    W, L, T, rh = 760, 250, 6, 34
    H = T + len(grp) * rh + 6
    mx = grp[0][1]
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Share of model impact by factor group">']
    for i, (k, v) in enumerate(grp):
        y = T + i * rh
        w = v / mx * (W - L - 70)
        cls = "b1" if i == 0 else "b0"
        out.append(f'<text x="{L-10}" y="{y+20}" text-anchor="end">{escape(k)}</text><rect x="{L}" y="{y+4}" width="{w:.1f}" height="22" class="{cls}"/><text x="{L+w+8:.1f}" y="{y+20}" class="strong">{v:.1f}%</text>')
    return "".join(out) + "</svg>"


def top_table():
    rows = []
    for i, (name, r) in enumerate(F.sort_values("shap", ascending=False).head(10).iterrows(), 1):
        rows.append(f'<tr><td>{i}</td><td>{escape(NAMES.get(name, name))}</td><td class="r">{r.shap:.1f}%</td><td class="r">±{r.swing:.1f}%</td></tr>')
    head = '<table><thead><tr><th>#</th><th>Factor</th><th class="r">Share of impact</th><th class="r">Typical effect on rent</th></tr></thead><tbody>'
    return head + "".join(rows) + "</tbody></table>"


def momentum_svg():
    W, H = 760, 190
    months = ["Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep"]
    bw = (W - 40) / len(months)
    cls = ["w6"] * 3 + ["w3"] * 3 + ["w0"] * 3 + ["gap"] * 2 + ["tgt"] * 2
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Which months the momentum factor compares">']
    for i, (m, c) in enumerate(zip(months, cls)):
        x = 20 + i * bw
        tc = "inbar" if c in ("w0", "w3", "w6") else "small"
        out.append(f'<rect x="{x:.1f}" y="40" width="{bw-3:.1f}" height="34" rx="4" class="{c}"/><text x="{x+bw/2-1.5:.1f}" y="62" text-anchor="middle" class="{tc}">{m}</text>')
    out.append(f'<text x="20" y="28" class="mut small">Sep 2025</text><text x="{20+9*bw-4:.1f}" y="28" text-anchor="end" class="mut small">data ends 31 May 2026</text><text x="{20+11*bw:.1f}" y="28" class="mut small">Aug-Sep 2026</text>')

    def lab(i0, n, t, y):
        return f'<text x="{20+(i0+n/2)*bw-1.5:.1f}" y="{y}" text-anchor="middle" class="small">{t}</text>'
    out.append(lab(0, 3, "Window 6 months back", 94) + lab(3, 3, "Window 3 months back", 94) + lab(6, 3, "Latest window = market level", 94) + lab(9, 2, "no data used", 94) + lab(11, 2, "judged adverts", 94))
    for (i0, i1, y, t) in [(6, 3, 124, "3-month momentum = latest level minus level 3 months back"), (6, 0, 158, "6-month momentum = latest level minus level 6 months back")]:
        xa, xb = 20 + (i0 + 1.5) * bw, 20 + (i1 + 1.5) * bw
        out.append(f'<path d="M{xa:.1f},{y-12} V{y} H{xb:.1f} V{y-12}" fill="none" class="brk"/><text x="{(xa+xb)/2:.1f}" y="{y+16}" text-anchor="middle" class="small">{t}</text>')
    return "".join(out) + "</svg>"


def pct(x):
    return f"{x:+.1f}%"


SH, ZE, CI = ME["Surry Hills 1-bed"], ME["Zetland 2-bed"], ME["city"]

FACTORS_HTML = f"""
<div class="card"><h3>What contributes most to the estimate</h3>
<div class="sub">Share of the model's impact on each prediction (mean absolute SHAP value on recent training adverts), grouped by type of factor.</div>
{groups_svg()}
<p class="note">The market level for the flat's suburb and bedroom count carries almost half of the weight. Bedroom count and suburb act mostly through that feature, so they look small on their own.</p>
<div class="sub" style="margin-top:14px">The ten single factors with the most impact</div>{top_table()}
<p class="note">"Typical effect" is the average size of that factor's push on a flat's predicted rent. Shares are relative: correlated factors, such as the flat's own rent and its building premium, share credit.</p></div>
"""

MOMENTUM_HTML = f"""
<div class="card"><h3>How the momentum factor is calculated</h3>
<div class="sub">Momentum tells the model how fast the market was moving in the months before the flat is rented.</div>
{momentum_svg()}
<ol>
<li><b>Market level.</b> For a flat's suburb and bedroom count we take the average of the log of weekly rent over a 3-month window of earlier adverts. When few adverts are in the window, it is pulled towards the city-wide average for that bedroom count so one odd advert cannot swing it.</li>
<li><b>Three-month lag.</b> Judged adverts fall 2 to 4 months after our last advert (31 May 2026), so every level and momentum value is taken as it stood 3 months before the advert date. For an August advert, the latest window is March to May. We trained the model on the same 3-month gap, so it learns what it will face.</li>
<li><b>Momentum.</b> 3-month momentum = latest level minus the level of the window 3 months earlier (December to February). 6-month momentum = latest level minus the level of the window 6 months earlier (September to November). City-wide momentum is the same 6-month change using all adverts in all suburbs. Differences in log rent are close to percentage changes.</li>
<li><b>Used with.</b> A related factor, market growth since the flat's own last advert, helps the model move that old rent up to today's level.</li></ol>
<div class="kpis"><div><div class="stat">{pct(SH['mom6_pct'])}</div><div class="note">Surry Hills one-bedrooms, geometric-mean asking rent: ${SH['W6']['rent']} (Sep-Nov 2025) to ${SH['W0']['rent']} (Mar-May 2026)</div></div>
<div><div class="stat">{pct(ZE['mom6_pct'])}</div><div class="note">Zetland two-bedrooms: ${ZE['W6']['rent']} to ${ZE['W0']['rent']} over the same 6 months</div></div>
<div><div class="stat">{pct(CI['mom6_pct'])}</div><div class="note">All suburbs and sizes: ${CI['W6']['rent']} to ${CI['W0']['rent']}, from {CI['W6']['n']:,} and {CI['W0']['n']:,} adverts</div></div></div>
<p class="note">Illustrative figures use simple averages of the cleaned adverts; the model's own momentum uses the shrunk market levels described above. Market momentum has cooled: rents are rising far more slowly than in 2022 and 2023.</p></div>
"""

SOURCES_HTML = """
<div class="card"><h3>Data sources we used</h3>
<table><thead><tr><th>Source</th><th>What it contains</th><th>How we used it</th></tr></thead><tbody>
<tr><td>Past leases file (supplied)</td><td>112,457 adverts for 52,296 flats, Jan 2012 to 31 Jul 2026: weekly rent, listing date, bedrooms, bathrooms, parking, type, coordinates</td><td>Target and history features. Adverts before 1 Jun 2026 built the model; 1 Jun to 31 Jul adverts only scored it. 2,785 error rows were dropped.</td></tr>
<tr><td>Input flats file (supplied)</td><td>65,777 flats in 33 suburbs: address, coordinates, type, bedrooms, bathrooms, parking, floor, flats in building, block homes counts</td><td>The flats we predict, and their attributes. Two block columns (homes in 2026, new homes 2021 to 2026) are model inputs.</td></tr>
<tr><td>Census blocks file (supplied)</td><td>2,281 blocks: homes and people in 2021 and 2026, new homes, block type</td><td>Tested. It did not improve accuracy on our validation, so the model does not use it beyond the two columns above.</td></tr>
<tr><td>Derived by us</td><td>Market level and momentum per suburb and bedroom count, each flat's own rent history, building and neighbour (250 m, 500 m) premiums over the market</td><td>Computed only from adverts dated at least 3 months before the flat's advert date, and never from after 31 Jul 2026.</td></tr>
<tr><td>Reviewed, not used</td><td>Microburbs API, G-NAF addresses, flat sales files</td><td>No outside data feeds the estimate. Sales prices, floor area and building age are the next things we would test.</td></tr>
</tbody></table>
<p class="note">Everything uses information dated by 31 Jul 2026. Event dates on the trend chart are for context only and are not model inputs.</p></div>
"""
