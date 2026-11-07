"""Builds submission/report.html (one self-contained page) from results/*.json and results/feature_impact.csv.
Run: python src/06_build_report.py"""
import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
S = json.load(open(RES / "report_stats.json"))
M = json.load(open(RES / "metrics.json"))
TREND = json.load(open(RES / "trend_rows.json"))
c, sp, pk = S["check"], S["split"], S["parking"]
APP_URL = "https://d4data-rent-estimator.vercel.app/"
fmt = lambda n: f"{int(round(n)):,}"
import datetime as _dt
nice = lambda iso: _dt.date.fromisoformat(iso).strftime("%-d %b %Y") if hasattr(_dt.date, "fromisoformat") and False else (lambda d: f"{d.day} {d.strftime('%b %Y')}")(_dt.date.fromisoformat(iso))
PK_WINDOW = f"{nice(pk['window'].split(' to ')[0])} to {nice(pk['window'].split(' to ')[1])}"
CHECK_WINDOW = f"{nice(sp['check_from'])} to {nice(sp['check_to'])}"
BUILD_WINDOW = f"{nice(sp['build_from'])} to {nice(sp['build_to'])}"

# ---------------------------------------------------------------- charts (inline SVG)
def trend_svg():
    W, H, L, R, T, B = 760, 330, 46, 60, 28, 34
    x0, x1 = 2015, 2026.75
    vals = [r["adj"] for r in TREND] + [r["raw"] for r in TREND]
    lo, hi = int(min(vals) // 10 * 10), int(-(-max(vals) // 10) * 10)
    X = lambda v: L + (v - x0) / (x1 - x0) * (W - L - R)
    Y = lambda v: T + (hi - v) / (hi - lo) * (H - T - B)
    path = lambda k: " ".join(("M" if i == 0 else "L") + f"{X(r['x']):.1f},{Y(r[k]):.1f}" for i, r in enumerate(TREND))
    bands = [(2020.17, 2020.42, "COVID"), (2021.92, 2022.17, "Borders reopen"), (2022.33, 2023.85, "Rate hikes")]
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Rent index 2015 to 2026">']
    for t in range(lo, hi + 1, 10):
        out.append(f'<line x1="{L}" x2="{W-R}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" class="grid"/><text x="{L-8}" y="{Y(t)+4:.1f}" text-anchor="end" class="mut">{t}</text>')
    for i, (a, b, lab) in enumerate(bands):
        out.append(f'<rect x="{X(a):.1f}" y="{T}" width="{X(b)-X(a):.1f}" height="{H-T-B}" class="band"/><text x="{X(a):.1f}" y="{T-6-(i%2)*11}" class="mut small">{lab}</text>')
    out.append(f'<line x1="{L}" x2="{W-R}" y1="{Y(100):.1f}" y2="{Y(100):.1f}" class="ref"/><text x="{L+6}" y="{Y(100)-5:.1f}" class="mut small">2019 average = 100</text>')
    out.append(f'<path d="{path("raw")}" class="rawline"/><path d="{path("adj")}" class="adjline"/>')
    low = min(TREND, key=lambda r: r["adj"]); last = TREND[-1]
    out.append(f'<circle cx="{X(low["x"]):.1f}" cy="{Y(low["adj"]):.1f}" r="4" class="dot"/><text x="{X(low["x"]):.1f}" y="{Y(low["adj"])+18:.1f}" text-anchor="middle" class="small">{low["q"]}: {low["adj"]:.0f}</text>')
    out.append(f'<circle cx="{X(last["x"]):.1f}" cy="{Y(last["adj"]):.1f}" r="4" class="dot"/><text x="{X(last["x"])+8:.1f}" y="{Y(last["adj"])+16:.1f}" class="acc">{last["adj"]:.0f}</text>')
    for y in range(2015, 2027):
        out.append(f'<text x="{X(y):.1f}" y="{H-12}" text-anchor="middle" class="mut">{y}</text>')
    out.append("</svg>")
    return "".join(out)


def grouped_bars_svg(rows):
    W, L, T, rh = 760, 120, 30, 46
    H = T + len(rows) * rh + 24
    mx = max(max(r["no_car"], r["with_car"]) for r in rows) * 1.12
    X = lambda v: L + v / mx * (W - L - 70)
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="One-bedroom median rent with and without a car space">',
           f'<rect x="{L}" y="6" width="12" height="12" class="b0"/><text x="{L+18}" y="16" class="mut small">No car space</text><rect x="{L+120}" y="6" width="12" height="12" class="b1"/><text x="{L+138}" y="16" class="mut small">With car space</text>']
    for i, r in enumerate(rows):
        y = T + i * rh
        out.append(f'<text x="{L-10}" y="{y+26}" text-anchor="end">{escape(r["suburb"])}</text>')
        out.append(f'<rect x="{L}" y="{y+4}" width="{X(r["no_car"])-L:.1f}" height="16" class="b0"/><text x="{X(r["no_car"])+6:.1f}" y="{y+17}" class="small">${r["no_car"]:,}</text>')
        out.append(f'<rect x="{L}" y="{y+22}" width="{X(r["with_car"])-L:.1f}" height="16" class="b1"/><text x="{X(r["with_car"])+6:.1f}" y="{y+35}" class="small strong">${r["with_car"]:,}</text>')
    out.append("</svg>")
    return "".join(out)


def buckets_svg():
    b = c["buckets"]; tot = c["n"]
    rows = [("$0 to $50", b["0-50"], "b1"), ("Over $50 to $100", b["50-100"], "b1"), ("Over $100 to $200", b["100-200"], "b2"), ("Over $200", b["200+"], "b2")]
    W, L, T, rh = 760, 150, 8, 40
    H = T + len(rows) * rh + 6
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="How far off the weekly rent estimates were">']
    for i, (lab, n, cls) in enumerate(rows):
        y = T + i * rh
        w = n / tot * (W - L - 130)
        out.append(f'<text x="{L-10}" y="{y+22}" text-anchor="end">{lab}</text><rect x="{L}" y="{y+6}" width="{W-L-130}" height="20" class="track"/><rect x="{L}" y="{y+6}" width="{w:.1f}" height="20" class="{cls}"/>'
                   f'<text x="{L+w+8:.1f}" y="{y+22}" class="strong">{n:,}</text><text x="{W-4}" y="{y+22}" text-anchor="end" class="mut">{n/tot*100:.1f}%</text>')
    out.append("</svg>")
    return "".join(out)


def timeline_svg():
    W, H = 760, 116
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="How adverts were split by date">']
    segs = [(20, 470, "b2", "Build: adverts to 31 May 2026", f"{sp['n_build']:,} adverts"),
            (490, 130, "b1", "Check: 1 Jun to 31 Jul", f"{c['n']:,} scored"),
            (630, 110, "hid", "Hidden test: 1 Aug to 30 Sep", "judges only")]
    for x, w, cls, a, b in segs:
        ly = 86 if cls != "hid" else 104
        out.append(f'<rect x="{x}" y="30" width="{w}" height="34" class="{cls}" rx="4"/><text x="{x+w/2}" y="52" text-anchor="middle" class="{"small" if cls == "hid" else "inbar"}">{b}</text><text x="{x+w/2 if cls != "hid" else 740}" y="{ly}" text-anchor="{"middle" if cls != "hid" else "end"}" class="small">{a}</text>')
    out.append('<text x="20" y="18" class="mut small">earliest advert Jan 2012</text><text x="740" y="18" text-anchor="end" class="mut small">time →</text></svg>')
    return "".join(out)


import sys
sys.path.insert(0, str(Path(__file__).parent))
from report_sections import FACTORS_HTML, MOMENTUM_HTML, SOURCES_HTML

HTML = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>d4data: Sydney flat rents, what drives them and how well we predict them</title>
<style>
:root{{--bg:#f5f8fc;--card:#fff;--ink:#0f1b2d;--mut:#5a6a80;--line:#dbe4f0;--b0:#a9c4e0;--b1:#1565b8;--b2:#6b8cab;--acc:#1565b8;--track:#d7e5f4;--band:#e4e9ef}}
@media(prefers-color-scheme:dark){{:root{{--bg:#0d1420;--card:#152033;--ink:#e8eef7;--mut:#9fb0c6;--line:#27364d;--b0:#5f7da0;--b1:#5fa2ee;--b2:#7a93ad;--acc:#7db4f5;--track:#243652;--band:#223046}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}}
.hero{{background:linear-gradient(135deg,#052a57,#1565b8);color:#fff;padding:54px 20px 46px;text-align:center}}
.hero .tag{{display:inline-block;font-size:12px;letter-spacing:.08em;text-transform:uppercase;background:rgba(255,255,255,.18);padding:5px 12px;border-radius:999px}}
.hero h1{{max-width:820px;margin:16px auto 0;font-size:clamp(26px,4.4vw,40px);line-height:1.15}}
main{{max-width:900px;margin:0 auto;padding:26px 18px 50px}}
.lead{{font-size:19px;color:var(--ink);max-width:760px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px 20px;margin:18px 0}}
.card h2,.card h3{{margin:0 0 4px;color:var(--acc)}} .card .sub{{color:var(--mut);font-size:14px;margin-bottom:10px}}
h2.sec{{margin:30px 0 6px;font-size:20px}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}@media(max-width:700px){{.grid2{{grid-template-columns:1fr}}}}
.stat{{font-size:44px;font-weight:800;color:var(--acc);line-height:1.05}} .stat small{{font-size:17px;font-weight:600;color:var(--mut)}}
.kpis{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:6px 0 10px}}@media(max-width:700px){{.kpis{{grid-template-columns:1fr}}}}
.note{{color:var(--mut);font-size:14px}} svg{{width:100%;height:auto;display:block}}
svg text{{fill:var(--ink);font:13px system-ui,sans-serif}}svg .mut{{fill:var(--mut)}}svg .small{{font-size:11.5px}}svg .strong{{font-weight:700}}svg .acc{{fill:var(--acc);font-weight:700}}svg .inbar{{fill:#fff;font-weight:600;font-size:12px}}
svg .grid{{stroke:var(--line)}}svg .ref{{stroke:var(--mut);stroke-dasharray:4 3}}svg .band{{fill:var(--band);opacity:.8}}
svg .rawline{{fill:none;stroke:var(--b0);stroke-width:1.8}}svg .adjline{{fill:none;stroke:var(--b1);stroke-width:2.8}}svg .dot{{fill:var(--b1)}}
svg .b0{{fill:var(--b0)}}svg .b1{{fill:var(--b1)}}svg .b2{{fill:var(--b2)}}svg .track{{fill:var(--track)}}svg .hid{{fill:none;stroke:var(--mut);stroke-dasharray:5 4}}
.bar{{height:14px;border-radius:7px;background:var(--track);overflow:hidden}}.bar i{{display:block;height:100%;background:var(--b1)}}
.flow{{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:8px 0}}.flow span{{background:var(--track);padding:7px 12px;border-radius:8px;font-size:14px;font-weight:600}}
table{{width:100%;border-collapse:collapse;font-size:14px}}th,td{{text-align:left;padding:7px 8px;border-bottom:1px solid var(--line);vertical-align:top}}th{{color:var(--mut)}}td.r,th.r{{text-align:right}}ol{{padding-left:20px}}ol li{{margin:6px 0}}
svg .w0{{fill:var(--b1)}}svg .w3{{fill:var(--b2)}}svg .w6{{fill:var(--b0)}}svg .gap{{fill:none;stroke:var(--mut);stroke-dasharray:4 3}}svg .tgt{{fill:var(--track)}}svg .brk{{stroke:var(--mut);stroke-width:1.5}}
ul{{margin:6px 0 0;padding-left:20px}} li{{margin:3px 0}} a{{color:var(--acc)}}
footer{{max-width:900px;margin:0 auto;padding:0 18px 36px;color:var(--mut);font-size:13px}}
</style></head><body>
<div class="hero"><span class="tag">Team d4data · Microburbs Hackathon · Rents task</span>
<h1>Sydney flat rents fell 17% in 2020, then climbed 32% above 2019. A car space now adds about $60 a week.</h1></div>
<main>
<p class="lead">Once flats are matched on suburb, bedrooms, bathrooms and type, a car space added about $60 a week (8%) to asking rent in 2024 onwards, about $3,120 over 52 weeks; the simple suburb-and-bedroom gap is larger, a median ${pk['median_premium']:.0f} across {pk['groups']} groups. We used past adverts to build a rent estimate for all 65,777 flats, with and without a car space. On {c['n']:,} later adverts that the estimate never saw, the typical miss was ${c['median_abs_error']:.0f} a week and {c['within_100']:.0f}% of estimates landed within $100 (R squared {c['r2']}). The organisers' baseline missed by $86 with 55.2% within $100.</p>

<div class="card"><h3>How rents moved, 2015 to July 2026</h3><div class="sub">Quarterly rent index, 2019 average = 100. Blue adjusts for suburb, bedrooms, bathrooms, parking and type; grey is the raw median. Shaded bands are approximate event dates; the last quarter covers July only.</div>
{trend_svg()}</div>

<h2 class="sec">What we found along the way</h2>
<div class="grid2">
<div class="card"><div class="stat">-17% <small>then +48%</small></div><p>Mix-adjusted rents bottomed at 83 (2019 = 100) in the last quarter of 2020, then rose 48% to late 2023. Three-bedroom flats fell furthest (28% from their peak). Other factors, such as supply and migration, moved at the same time, so this is timing, not proof of cause.</p></div>
<div class="card"><div class="stat">$60 <small>a week for parking</small></div><p>Median gap in matched groups (same suburb, bedrooms, bathrooms and type) from 2024 onwards. It was close to zero before COVID, about $10 during it and $23 in 2022 to 2023. The cruder suburb-and-bedroom gap is ${pk['median_premium']:.0f} a week across {pk['groups']} groups with at least 10 adverts for both parking choices ({PK_WINDOW}); it is bigger because flats with parking also tend to be larger.</p></div>
<div class="card"><div class="stat">44% <small>from bedrooms</small></div><p>Bedrooms explain 44% of the variation in rent; suburb alone explains 18%. Current median adverts run from $510 for a studio to $750 for one bedroom, $1,050 for two and $1,500 for three.</p></div>
<div class="card"><div class="stat">2-5% <small>a year</small></div><p>Rent growth on the same flat cooled to 2-5% a year now, from 8-10% a year in 2022 and 2023. Rents are still 31-37% above their pre-COVID level.</p></div>
</div>

<div class="card"><h3>One-bedroom flats: median weekly asking rent</h3><div class="sub">The four busiest suburb groups with at least 10 adverts for each parking choice, {PK_WINDOW}.</div>
{grouped_bars_svg(S['parking_1bed'])}
<p class="note">These are raw suburb-and-bedroom gaps, so other flat differences (for example size and bathrooms) account for part of each gap; the matched figure is about $60.</p></div>

<div class="card"><h3>What our separate check showed</h3><div class="sub">R squared is the share of variation in weekly rent the estimate explains.</div>
<div class="kpis"><div><div class="stat">${c['median_abs_error']:.0f}<small> a week</small></div><div class="note">Typical miss (median absolute error) on {c['n']:,} later adverts, {CHECK_WINDOW}</div></div>
<div><div class="stat">{c['within_100']}%</div><div class="note">{c['buckets']['0-50']+c['buckets']['50-100']:,} of {c['n']:,} estimates within $100 a week</div></div>
<div><div class="stat">{c['r2']}</div><div class="note">R squared on the later adverts</div></div></div>
<div class="bar"><i style="width:{c['within_100']}%"></i></div>
<div class="note" style="display:flex;justify-content:space-between"><span>{c['buckets']['0-50']+c['buckets']['50-100']:,} within $100</span><span>{c['buckets']['100-200']+c['buckets']['200+']:,} more than $100 away</span></div>
<p class="note">Organisers' baseline for comparison: $86 typical miss, 55.2% within $100. We built the estimate using only adverts dated before 1 Jun 2026 and scored the later adverts once the model was fixed. The hidden 1 Aug to 30 Sep 2026 adverts give the official score.</p></div>

<div class="card"><h3>How far off was each weekly rent estimate?</h3><div class="sub">{c['n']:,} adverts from {CHECK_WINDOW}</div>{buckets_svg()}</div>

<div class="card"><h3>How we split the adverts by date</h3><div class="sub">Earlier adverts built the estimate; later adverts, dated by 31 Jul 2026, checked it. Nothing after 31 Jul 2026 was used anywhere.</div>{timeline_svg()}</div>

{FACTORS_HTML}
{MOMENTUM_HTML}
{SOURCES_HTML}
<div class="grid2">
<div class="card"><h3>What data supported the result?</h3>
<p>{sp['n_build']:,} earlier adverts from the supplied lease file ({BUILD_WINDOW}) built the estimate, after removing {sp['n_dropped_flagged']:,} rows we flagged as errors (for example 10 or more bedrooms, or rents far out of line with their suburb, bedroom count and year). {sp['n_check_all']:,} later adverts tested it; {c['n']:,} had a known parking state and were scored.</p>
<p>We predicted all 65,777 flats in the supplied input list (33 suburbs) and used its coordinates, bedrooms, bathrooms, parking, floor and building size. We also looked at the census block file; it did not improve accuracy so the model does not use it. No other outside data was used.</p></div>
<div class="card"><h3>How did we estimate rent?</h3>
<p>A gradient-boosted tree model (LightGBM) predicts the log of weekly rent, with an absolute-error loss so it targets the typical miss. It looks at the recent market rent for the flat's suburb and bedrooms and how fast it is moving, the flat's own past rents, how its building and nearby buildings compare with the market, and bedrooms, bathrooms, type, floor and parking. We predict every flat twice, with and without a car space, and never let the with-parking rent fall below the without-parking rent.</p>
<div class="flow"><span>Earlier adverts</span>→<span>Market level, own history, building and neighbours</span>→<span>LightGBM</span>→<span>Rent with / without car space</span></div></div>
<div class="card"><h3>How did we check it?</h3>
<p>We held out every advert dated 1 Jun to 31 Jul 2026 and did not use them to build or tune the model. Model settings were chosen on April to May 2026 inside the earlier adverts. We scored three candidate models on the later adverts (a median baseline, a first LightGBM and the final one) and kept the best; the median baseline missed by $90 and the first LightGBM by $46.5. We did not retrain on the later adverts.</p>
<p class="note">Typical miss by bedrooms on the later adverts: studio ${S['check_by_beds']['0']['median_abs_error']:.0f}, one bed ${S['check_by_beds']['1']['median_abs_error']:.0f}, two beds ${S['check_by_beds']['2']['median_abs_error']:.0f}, three beds ${S['check_by_beds']['3']['median_abs_error']:.0f}; with a car space ${S['check_by_parking']['with car space']['median_abs_error']:.0f}, without ${S['check_by_parking']['without car space']['median_abs_error']:.0f}.</p></div>
<div class="card"><h3>What remains uncertain?</h3>
<ul><li>The judged adverts fall 2 to 4 months after our last training advert, so the real miss may be larger. A July-only check, trained through June, gave about $50 for our first model.</li>
<li>Flats with no rent history are harder (about $66 typical miss against $42 in our April to May validation), as are three-bedrooms, rents above $1,300 and waterfront or luxury areas such as Barangaroo and Millers Point.</li>
<li>The estimates ran about {abs(c['median_signed_pct']):.1f}% {'above' if c['median_signed_pct']>0 else 'below'} actual rents on the median in the later adverts. Rents kept moving after the training data ended, so bias could be larger in August and September.</li>
<li>The check set is {c['n']:,} adverts; gaps of a few dollars between models are within noise. The COVID and rate-event dates are approximate.</li>
<li>We have not used floor area, building age or sale prices; those need a new dated check before claiming improvement.</li></ul></div>
</div>

<div class="card"><h3>Try it</h3><p>Our rent estimator app lets you look up a flat or describe a property and see a rent heat map: <a href="{APP_URL}">{APP_URL}</a>.</p></div>
</main>
<footer>Team d4data. Research for informational purposes only; not financial advice or a formal valuation. Adverts and the supplied flat list come from the Microburbs hackathon files; all figures use information dated by 31 Jul 2026.</footer>
</body></html>"""
out = ROOT / "submission" / "report.html"
out.write_text(HTML, encoding="utf-8")
print("wrote", out, f"({out.stat().st_size/1e3:.0f} KB)")
