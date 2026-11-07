"""Builds landing/index.html: one self-contained promo/landing page (CSS inline, charts as inline SVG, screenshots embedded as base64).
Run: python src/07_build_landing.py   (needs results/*.json, landing/img/*.jpg)"""
import base64
import json
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "landing"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import report_sections as ES  # noqa: E402  (feature-impact groups chart)

TREND = json.load(open(ROOT / "results" / "trend_rows.json"))
M = json.load(open(ROOT / "results" / "metrics.json"))
S = json.load(open(ROOT / "results" / "report_stats.json"))
APP = "https://d4data-rent-estimator.vercel.app/"
REPO = "https://github.com/satishpoks/microburbs-rent-task"
c = S["check"]


def img64(name):
    return "data:image/jpeg;base64," + base64.b64encode((HERE / "img" / name).read_bytes()).decode()


# ------------------------------------------------------------------ charts
def trend_svg():
    W, H, L, R, T, B = 760, 340, 46, 60, 34, 34
    x0, x1 = 2015, 2026.75
    vals = [r["adj"] for r in TREND] + [r["raw"] for r in TREND]
    lo, hi = int(min(vals) // 10 * 10), int(-(-max(vals) // 10) * 10)
    X = lambda v: L + (v - x0) / (x1 - x0) * (W - L - R)
    Y = lambda v: T + (hi - v) / (hi - lo) * (H - T - B)
    path = lambda k: " ".join(("M" if i == 0 else "L") + f"{X(r['x']):.1f},{Y(r[k]):.1f}" for i, r in enumerate(TREND))
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Mix-adjusted Sydney rent index 2015 to July 2026">']
    for t in range(lo, hi + 1, 10):
        o.append(f'<line x1="{L}" x2="{W-R}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" class="grid"/><text x="{L-8}" y="{Y(t)+4:.1f}" text-anchor="end" class="mut">{t}</text>')
    for i, (a, b, lab) in enumerate([(2020.17, 2020.42, "COVID"), (2021.92, 2022.17, "Borders reopen"), (2022.33, 2023.85, "Rate hikes")]):
        o.append(f'<rect x="{X(a):.1f}" y="{T}" width="{X(b)-X(a):.1f}" height="{H-T-B}" class="band"/><text x="{X(a):.1f}" y="{T-6-(i%2)*11}" class="mut small">{lab}</text>')
    o.append(f'<line x1="{L}" x2="{W-R}" y1="{Y(100):.1f}" y2="{Y(100):.1f}" class="ref"/><text x="{L+6}" y="{Y(100)-5:.1f}" class="mut small">2019 average = 100</text>')
    o.append(f'<path d="{path("raw")}" class="rawline"/><path d="{path("adj")}" class="adjline"/>')
    low, last = min(TREND, key=lambda r: r["adj"]), TREND[-1]
    o.append(f'<circle cx="{X(low["x"]):.1f}" cy="{Y(low["adj"]):.1f}" r="4.5" class="dot"/><text x="{X(low["x"]):.1f}" y="{Y(low["adj"])+19:.1f}" text-anchor="middle" class="small strong">{low["q"]}: {low["adj"]:.1f}</text>')
    o.append(f'<circle cx="{X(last["x"]):.1f}" cy="{Y(last["adj"]):.1f}" r="4.5" class="dot"/><text x="{X(last["x"])+8:.1f}" y="{Y(last["adj"])+16:.1f}" class="acc">{last["adj"]:.0f}</text>')
    for y in range(2015, 2027):
        o.append(f'<text x="{X(y):.1f}" y="{H-12}" text-anchor="middle" class="mut">{y}</text>')
    return "".join(o) + "</svg>"


def car_svg():
    rows = [("Pre-COVID", -5), ("COVID", 10), ("Reopening", 23), ("2024 on", 60)]
    W, H, L, R, T, B = 760, 280, 30, 20, 30, 50
    lo, hi = -20, 70
    Y = lambda v: T + (hi - v) / (hi - lo) * (H - T - B)
    band = (W - L - R) / len(rows)
    bw = band * 0.5
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Car space premium by period">']
    for i, (lab, v) in enumerate(rows):
        x = L + i * band + (band - bw) / 2
        cls = "b1" if i == len(rows) - 1 else "b0"
        txt = ("-" if v < 0 else "") + f"${abs(v)}"
        ty = Y(v) - 8 if v >= 0 else Y(v) + 18
        o.append(f'<rect x="{x:.1f}" y="{min(Y(0), Y(v)):.1f}" width="{bw:.1f}" height="{abs(Y(v)-Y(0)):.1f}" class="{cls}" rx="3"/><text x="{x+bw/2:.1f}" y="{ty:.1f}" text-anchor="middle" class="strong">{txt}</text><text x="{x+bw/2:.1f}" y="{H-B+24}" text-anchor="middle" class="mut">{lab}</text>')
    o.append(f'<line x1="{L}" x2="{W-R}" y1="{Y(0):.1f}" y2="{Y(0):.1f}" class="axis"/>')
    return "".join(o) + "</svg>"


def models_svg():
    rows = [("Median baseline", M["baseline_median"]["median_abs_error"], M["baseline_median"]["within_100"] * 100, False),
            ("LightGBM v1", M["lightgbm_v1"]["median_abs_error"], M["lightgbm_v1"]["within_100"] * 100, False),
            ("LightGBM v2 (submitted)", M["lightgbm_v2"]["median_abs_error"], M["lightgbm_v2"]["within_100"] * 100, True)]
    W, L, T, rh = 760, 190, 10, 52
    H = T + len(rows) * rh + 10
    mx = max(r[1] for r in rows) * 1.05
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Typical weekly miss by model">']
    for i, (lab, med, w100, hl) in enumerate(rows):
        y = T + i * rh
        w = med / mx * (W - L - 210)
        o.append(f'<text x="{L-10}" y="{y+30}" text-anchor="end" {"class=strong" if hl else ""}>{lab}</text><rect x="{L}" y="{y+8}" width="{w:.1f}" height="30" class="{"b1" if hl else "b0"}" rx="3"/><text x="{L+w+10:.1f}" y="{y+29}" class="strong">${med:.1f}</text><text x="{L+w+70:.1f}" y="{y+29}" class="mut">{w100:.1f}% within $100</text>')
    o.append(f'<line x1="{L}" x2="{L}" y1="{T}" y2="{H-6}" class="axis"/>')
    return "".join(o) + "</svg>"


# ------------------------------------------------------------------ page
CSS = """
:root{--blue:#2A78D6;--navy:#14233C;--grey:#C4C3B7;--pale:#F4F3EE;--green:#E3F3E8;--red:#FBE4E1;--ink:#14233C;--mut:#5b6a80;--card:#fff;--line:#e2e1d9;--bg:#F4F3EE}
@media(prefers-color-scheme:dark){:root{--ink:#e9eef6;--mut:#a3b2c7;--card:#18263b;--line:#2b3b55;--bg:#0f1a2b;--pale:#0f1a2b;--green:#173a2a;--red:#46222a;--grey:#6b7a90}}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.6 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
a{color:var(--blue)}nav{position:sticky;top:0;z-index:10;background:rgba(20,35,60,.96);backdrop-filter:blur(6px);color:#fff}
nav .in{max-width:1080px;margin:0 auto;padding:10px 18px;display:flex;gap:18px;align-items:center;flex-wrap:wrap}nav b{margin-right:auto}nav a{color:#cfe0f7;text-decoration:none;font-size:14px}nav a:hover{color:#fff}
.btn{display:inline-block;padding:12px 22px;border-radius:999px;font-weight:700;text-decoration:none;border:2px solid transparent}.btn.p{background:var(--blue);color:#fff}.btn.s{background:transparent;color:#fff;border-color:#9bbfee}
nav .btn{padding:7px 16px;font-size:14px;color:#fff;background:var(--blue)}
.hero{background:radial-gradient(1200px 500px at 20% -10%,#2a78d6 0,transparent 60%),linear-gradient(160deg,#0c1a31,#14233C 60%,#1d3f73);color:#fff;padding:70px 18px 60px;text-align:center}
.hero h1{max-width:900px;margin:0 auto;font-size:clamp(30px,5.2vw,52px);line-height:1.1;letter-spacing:-.01em}.hero p.sub{max-width:720px;margin:18px auto 0;font-size:clamp(17px,2.2vw,21px);color:#dce8f8}
.by{margin-top:14px;font-size:14px;color:#9fb6d6}.cta{margin-top:26px;display:flex;gap:12px;justify-content:center;flex-wrap:wrap}
.tiles{max-width:1000px;margin:36px auto 0;display:grid;grid-template-columns:repeat(4,1fr);gap:14px}@media(max-width:800px){.tiles{grid-template-columns:1fr 1fr}}
.tile{background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.18);border-radius:16px;padding:18px 12px}.tile b{display:block;font-size:clamp(30px,4.6vw,44px);line-height:1}.tile span{display:block;margin-top:8px;font-size:14px;color:#cfe0f7}
.fine{margin-top:14px;font-size:13px;color:#9fb6d6}
main{max-width:1080px;margin:0 auto;padding:0 18px 40px}section{padding:56px 0 8px}section h2{font-size:clamp(26px,3.6vw,36px);line-height:1.15;margin:0 0 8px}.lead{font-size:19px;color:var(--mut);max-width:780px}
figure{margin:20px 0;background:var(--card);border:1px solid var(--line);border-radius:16px;padding:14px;overflow:hidden}figure img{width:100%;height:auto;display:block;border-radius:10px}figcaption{font-size:13.5px;color:var(--mut);margin-top:8px}svg{width:100%;height:auto;display:block}
.cards{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:22px}@media(max-width:800px){.cards{grid-template-columns:1fr}}.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:20px}.card.wide{grid-column:1/-1}
.big{font-size:clamp(30px,4.4vw,42px);font-weight:800;color:var(--blue);line-height:1.05}.card h3{margin:6px 0 6px;font-size:19px}.card p{margin:6px 0 0;color:var(--mut);font-size:16px}
.callout{margin:24px 0;padding:18px 20px;border-radius:14px;background:var(--card);border:1px solid var(--line);border-left:6px solid var(--blue)}.callout b{display:block;margin-bottom:4px}.callout.warn{border-left-color:#d68a2a}
.tw{overflow-x:auto;margin:16px 0;background:var(--card);border:1px solid var(--line);border-radius:14px}table{width:100%;border-collapse:collapse;font-size:15px;min-width:560px}th,td{padding:10px 12px;text-align:left;border-bottom:1px solid var(--line)}th{color:var(--mut);font-size:13px;text-transform:uppercase;letter-spacing:.04em}tr:last-child td{border-bottom:0}td.n,th.n{text-align:right}
td.g{background:var(--green)}td.r{background:var(--red)}.note{font-size:13.5px;color:var(--mut)}
.tl{display:grid;grid-template-columns:2fr 1fr 1fr;gap:12px;margin:22px 0}@media(max-width:800px){.tl{grid-template-columns:1fr}}.tl div{border-radius:14px;padding:16px;color:#fff}.tl .a{background:#4d6c8f}.tl .b{background:var(--blue)}.tl .c{background:transparent;border:2px dashed var(--mut);color:var(--ink)}.tl b{display:block;font-size:19px}.tl span{font-size:14px;opacity:.92}
ul.l{padding-left:20px}ul.l li{margin:7px 0}.chips{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}.chips span{background:var(--card);border:1px solid var(--line);border-radius:999px;padding:6px 14px;font-weight:600;font-size:15px}
code{background:var(--card);border:1px solid var(--line);padding:1px 6px;border-radius:6px;font-size:14px}
.cta2{background:linear-gradient(160deg,#14233C,#1d3f73);color:#fff;border-radius:22px;padding:34px 22px;text-align:center;margin:30px 0}.cta2 h2{margin:0 0 10px}
footer{background:var(--navy);color:#b9c8de;padding:28px 18px;font-size:13.5px;text-align:center}footer div{max-width:820px;margin:0 auto}
svg text{fill:var(--ink);font:13px system-ui,sans-serif}svg .mut{fill:var(--mut)}svg .small{font-size:11.5px}svg .strong{font-weight:700}svg .acc{fill:var(--blue);font-weight:700}svg .grid{stroke:var(--line)}svg .ref{stroke:var(--mut);stroke-dasharray:4 3}svg .band{fill:var(--grey);opacity:.35}svg .axis{stroke:var(--mut)}
svg .rawline{fill:none;stroke:var(--grey);stroke-width:2}svg .adjline{fill:none;stroke:var(--blue);stroke-width:3}svg .dot{fill:var(--blue)}svg .b0{fill:var(--grey)}svg .b1{fill:var(--blue)}
"""


def pc(x):  # coloured % cell
    return x


periods = [
    ("Pre-COVID (Jan 2015 to Feb 2020)", "33,316", [630, 390, 560, 765, 1100], None),
    ("COVID (Mar 2020 to Nov 2021)", "22,479", [580, 350, 500, 680, 890], [-8, -10, -11, -11, -19]),
    ("Reopening (Dec 2021 to Dec 2023)", "18,410", [730, 430, 650, 900, 1350], [16, 10, 16, 18, 23]),
    ("Current (Jan 2024 on)", "37,863", [850, 510, 750, 1050, 1500], [35, 31, 34, 37, 36]),
]


def periods_rows():
    out = []
    for name, n, vals, chg in periods:
        cells = ""
        for i, v in enumerate(vals):
            if chg is None:
                cells += f'<td class="n">${v:,}</td>'
            else:
                cls = "g" if chg[i] > 0 else "r"
                sign = "+" if chg[i] > 0 else "−"
                cells += f'<td class="n {cls}">${v:,} ({sign}{abs(chg[i])}%)</td>'
        out.append(f"<tr><td>{name}</td><td class='n'>{n}</td>{cells}</tr>")
    return "".join(out)


HTML = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>What should a Sydney flat rent for this week? | d4data rent estimator</title>
<meta name="description" content="A rent estimate for 65,777 City of Sydney flats. Typical miss $44 a week, 79.2% within $100, R squared 0.888 on a held-out check. Built for the Microburbs Hackathon.">
<style>{CSS}</style></head><body>
<nav><div class="in"><b>d4data</b><a href="#insights">Insights</a><a href="#accuracy">Accuracy</a><a href="#date-split">Date split</a><a href="#data">Data</a><a href="#method">Method</a><a href="#limits">Limits</a><a href="#app">Try the app</a><a class="btn" href="{APP}">Open the live app</a></div></nav>

<header class="hero" id="top">
<h1>Rents fell 17%, then climbed 48%. So what should your flat rent for this week?</h1>
<p class="sub">We built a rent estimator for all 65,777 City of Sydney flats. Four in five estimates land within $100 of the real asking rent, and we'll show you exactly how we checked.</p>
<div class="by">Team d4data &middot; Microburbs Hackathon, Rents task &middot; 7 November 2026</div>
<div class="cta"><a class="btn p" href="{APP}">Check a flat now</a><a class="btn s" href="#insights">See what we found</a></div>
<div class="tiles">
<div class="tile"><b>$44</b><span>our typical miss, per week</span></div>
<div class="tile"><b>79.2%</b><span>of estimates within $100</span></div>
<div class="tile"><b>0.888</b><span>R squared (how much of rent we explain)</span></div>
<div class="tile"><b>65,777</b><span>flats priced, with and without parking</span></div></div>
<div class="fine">Scored on {c['n']:,} adverts the model never saw while it was being built.</div>
</header>
<main>
<figure style="margin-top:-24px;position:relative"><img src="{img64('fig-app-hero.jpg')}" alt="The d4data Sydney Rent Estimator showing a predicted weekly rent and comparable flats for one address."><figcaption>The live estimator: a predicted weekly rent for one address, with charts for similar flats.</figcaption></figure>

<section id="insights"><h2>What 112,457 past adverts told us</h2><p class="lead">We went looking for the story in a decade of rent adverts. These six things stood out.</p>
<div class="cards">
<div class="card wide"><div class="big">&minus;17% then +48%</div><h3>The 2020 dip wiped out 17%. The rebound added 48%.</h3><p>After adjusting for suburb, bedrooms, bathrooms, parking and type, rents ended 2020 at 17% below their 2019 average. By late 2023 they had climbed 48% from that low. They now sit 32% above 2019. Three-bedroom flats fell hardest, 28% from their peak.</p>
<figure style="margin-bottom:0"><div id="fig-rent-index">{trend_svg()}</div><figcaption>Blue is the mix-adjusted index (2019 = 100), grey is the raw median. Shaded bands are approximate event dates, used for orientation only. The last point covers July 2026 only.</figcaption></figure></div>
<div class="card wide"><div class="big">$60 a week</div><h3>A car space went from worth nothing to about $3,100 a year.</h3><p>Before COVID, flats with and without a car space asked about the same rent (the gap was around &minus;$5 a week). From 2024 on, the gap is about $60 a week, or +8%. That is roughly $3,100 a year ($60 &times; 52).</p>
<figure style="margin-bottom:0"><div id="fig-car-premium">{car_svg()}</div><figcaption>Median weekly gap between flats with and without a car space, matched on suburb, bedrooms, bathrooms and type.</figcaption></figure></div>
<div class="card"><div class="big">2% to 5%</div><h3>The market is cooling.</h3><p>Compare a flat's rent with its own previous advert. In 2022 and 2023 that jump was 8% to 10% a year. Now it is 2% to 5%.</p></div>
<div class="card"><div class="big">44%</div><h3>Bedrooms beat postcodes.</h3><p>Bedrooms alone explain 44% of rent variation. Suburb alone explains 18%. Together they explain 55%. Size matters more than twice as much as location.</p></div>
<div class="card"><div class="big">Hardest</div><h3>The easy flats are easy. The glamorous ones are hard.</h3><p>Our biggest misses are waterfront and luxury areas like Barangaroo, Millers Point and Pyrmont, plus three-bedroom flats and flats with no rent history.</p></div>
<div class="card"><div class="big">2.5%</div><h3>One field in the data quietly changes meaning.</h3><p><code>was_leased</code> marks 3% of adverts in 2015 and 88% in 2026. It does not mean the same thing across years, so we threw it out. Roughly 2.5% of past adverts also looked like errors, and we flagged them.</p></div></div>
<div class="callout" id="next-window"><b>What does this mean for August and September?</b>Same-flat growth of 2% to 5% a year works out to roughly $5 to $10 a week of market movement over three months on a typical $900 rent. That is far smaller than our typical $44 miss. So for this window, getting each flat's level right matters more than guessing the trend. We have not tested how this holds further out, so we are not forecasting past September 2026.</div>
<h3>The same market, four moods</h3>
<div class="tw"><table><thead><tr><th>Period</th><th class="n">Adverts</th><th class="n">All</th><th class="n">Studio</th><th class="n">1 bed</th><th class="n">2 bed</th><th class="n">3 bed</th></tr></thead><tbody>{periods_rows()}</tbody></table></div>
<p class="note">Median weekly rent by bedrooms, raw adverts. Green is above the pre-COVID level, red is below. Event dates are approximate.</p>
<div class="tw"><table><thead><tr><th>Car space premium</th><th class="n">Matched cells</th><th class="n">Gap ($ a week)</th><th class="n">Gap (%)</th></tr></thead><tbody>
<tr><td>Pre-COVID</td><td class="n">179</td><td class="n">&minus;$5</td><td class="n">&minus;0.7%</td></tr><tr><td>COVID</td><td class="n">232</td><td class="n">$10</td><td class="n">+1.6%</td></tr><tr><td>Reopening</td><td class="n">248</td><td class="n">$23</td><td class="n">+4.0%</td></tr><tr><td>Current</td><td class="n">293</td><td class="n">$60</td><td class="n">+8.2%</td></tr></tbody></table></div></section>

<section id="accuracy"><h2>So how good is it, honestly?</h2><p class="lead">We hid {c['n']:,} adverts from the model. Then we asked it to guess their rents. It missed by a median of $44.1 a week, placed 79.2% within $100, and explained 88.8% of the variation in rent (R&sup2; 0.888).</p>
<div class="tw"><table><thead><tr><th>Model</th><th class="n">Typical weekly miss</th><th class="n">Within $100</th><th class="n">R&sup2;</th></tr></thead><tbody>
<tr><td>Our median baseline (suburb by bedrooms)</td><td class="n">$90</td><td class="n">58.5%</td><td class="n">0.72</td></tr>
<tr><td>LightGBM v1</td><td class="n">$46.5</td><td class="n">78.3%</td><td class="n">0.885</td></tr>
<tr><td><b>LightGBM v2 (submitted)</b></td><td class="n"><b>$44.1</b></td><td class="n"><b>79.2%</b></td><td class="n"><b>0.888</b></td></tr></tbody></table></div>
<figure><div id="fig-model-comparison">{models_svg()}</div><figcaption>Typical weekly miss on {c['n']:,} held-out adverts (1 June to 31 July 2026). Shorter is better.</figcaption></figure>
<div class="callout"><b>In plain English</b>The typical miss is the median gap between our estimate and the advertised rent. R squared is the share of weekly rent variation our estimate explains.</div>
<div class="callout warn"><b>Fair warning</b>The organisers' baseline missed by $86 a week and placed 55.21% of adverts within $100 on the frozen August to September set. We have not seen those adverts, so we cannot compare head-to-head. Our numbers come from an earlier check.</div>
<h3>Where it misses most</h3>
<div class="tw"><table><thead><tr><th>Segment</th><th class="n">Typical weekly miss</th></tr></thead><tbody><tr><td>Flats with rent history</td><td class="n">$42</td></tr><tr><td>Flats with no rent history (24.5% of flats)</td><td class="n">$66</td></tr><tr><td>Three-bedroom flats</td><td class="n">$82</td></tr><tr><td>Rents above $1,300 a week</td><td class="n">Higher</td></tr></tbody></table></div>
<p class="note">Segment figures come from our April to May 2026 validation slice, inside the build period.</p></section>

<section id="date-split"><h2>How we made sure we didn't cheat</h2><p class="lead">A rent model that has already seen the answers will look brilliant and be useless. So we split adverts by date.</p>
<div class="tl"><div class="a"><b>Build</b><span>Before 1 June 2026. All training and tuning used only these adverts.</span></div><div class="b"><b>Check</b><span>1 June to 31 July 2026. {c['n']:,} adverts, scored once the method was set.</span></div><div class="c"><b>Judged</b><span>1 August to 30 September 2026. 1,699 frozen adverts we have never seen.</span></div></div>
<p><b>Our rules</b></p><ul class="l"><li>Settings were chosen using only the training period.</li><li>Check adverts never went into building or tuning the method.</li><li>Baselines and our first model were scored on the same check for comparison. We picked the final model by a rule fixed before testing.</li><li>Nothing dated after 31 July 2026 is used anywhere.</li></ul></section>

<section id="data"><h2>What we worked with</h2>
<div class="tw"><table><thead><tr><th>Dataset</th><th class="n">Rows</th><th>Coverage</th><th>Role</th></tr></thead><tbody>
<tr><td>Past adverts</td><td class="n">112,457</td><td>Jan 2012 to Jul 2026, 52,296 flats</td><td>Training and market trend</td></tr>
<tr><td>Input flats</td><td class="n">65,777</td><td>33 City of Sydney suburbs</td><td>The flats to price</td></tr>
<tr><td>Census blocks</td><td class="n">2,281</td><td>Home and people counts, 2021 and 2026</td><td>Tested, added no accuracy</td></tr></tbody></table></div>
<p><b>The messy bits, because every dataset has them</b></p><ul class="l">
<li>24.5% of flats have no past advert at all, so we lean on market and building signals for them.</li><li>Bedrooms match the latest advert for 98.3% of flats, bathrooms for 99.5%, car space for 87.4%.</li><li>Car space is missing for 8.8% of flats and floor level for 47.7%.</li><li>143 flats have unusual attributes. We kept them, because every flat needs a prediction.</li><li>Dropping flagged adverts moved suburb-by-bedroom medians by only 1.7%.</li><li>Volumes are thin before 2015, so trend work starts in 2015.</li></ul>
<p class="note">The raw data is private, so we only show aggregates.</p></section>

<section id="method"><h2>How the estimate works</h2><p class="lead">We used LightGBM to predict log rent with an absolute-error loss. That means a few outlandish adverts cannot drag the whole estimate around, which matters in a market with $5,000-a-week outliers.</p>
<div class="chips"><span>Market</span><span>Rent history</span><span>Building</span><span>The flat</span><span>Parking</span></div>
<div class="callout"><b>The parking rule</b>Every flat gets two predictions, with and without a car space, and rent with parking is never below rent without. The app cannot tell you parking makes a flat cheaper.</div>
<figure><div id="fig-shap">{ES.groups_svg()}</div><figcaption>Share of model impact by factor group. In practice the model first works out where the market is today, then adjusts for the specific flat.</figcaption></figure>
<div class="callout"><b>Reproducibility</b>Final model: LightGBM, objective L1 on log weekly rent, learning rate 0.05, 63 leaves, minimum 40 rows per leaf, 80% feature and row sampling, about 610 boosting rounds, seed 7; recent adverts weighted more (half-life 3 years). 40 features across the five groups above. Code: <a href="{REPO}">{REPO}</a> (<code>src/02_baseline.py</code>, <code>src/03_model_v2.py</code>).</div>
<div class="callout"><b>How the contest judges us</b>Median absolute dollar error on 1,699 frozen adverts, with the share within $100 breaking ties. The scored rent comes from the column matching the advert's parking, and empty answers count worse than answered errors. That is why every flat has both predictions and no blanks.</div></section>

<section id="limits"><h2>Where we're least sure</h2><p class="lead">We'd rather tell you than have you find out.</p>
<ul class="l"><li><b>The real test is further out.</b> The judged adverts fall two to four months after our last training data, so the real error could be higher. A July-only check gave $50 for our first model.</li>
<li><b>Our check set is modest.</b> A few dollars' gap between models is within noise. A five-variant ensemble matched v2 on median error ($44.7) and scored a better R&sup2; (0.897). We kept v2 because we had set the rule in advance.</li>
<li><b>We haven't used everything yet:</b> June and July market trends, floor area, building age and the flat sales files.</li>
<li><b>These are asking-rent estimates.</b> They are not valuations or financial advice.</li></ul></section>

<section id="app"><h2>Search your own address. Does the number feel right?</h2>
<div class="cards"><div class="card"><h3>Find my flat</h3><p>Search an address for the model's prediction, a rent-by-bedrooms chart, a heat map and comparable flats.</p></div><div class="card"><h3>Describe a property</h3><p>Pick suburb, bedrooms, type and parking to see what real matching flats suggest.</p></div></div>
<figure><img src="{img64('fig-app-describe.jpg')}" alt="The estimator's Describe a property mode with filters and an estimate for two-bedroom flats in Surry Hills." loading="lazy"><figcaption>Describe a property: filters on the left, an estimate with a range and confidence on the right.</figcaption></figure>
<figure style="max-width:520px;margin-left:auto;margin-right:auto"><img src="{img64('fig-app-heatmap.jpg')}" alt="OpenStreetMap heat map of median predicted weekly rent in 200 metre squares." loading="lazy"><figcaption>The rent heat map on OpenStreetMap: median predicted weekly rent per 200 m square.</figcaption></figure>
<div class="cards"><div class="card"><h3>Tenants</h3><p>Is this asking rent in line with nearby flats?</p></div><div class="card"><h3>Landlords</h3><p>What does parking change about the price?</p></div><div class="card wide"><h3>Agents</h3><p>How does this suburb compare for the same flat type?</p></div></div>
<div class="cta2"><h2>Ready to test it?</h2><p>Open the estimator and try your own address.</p><a class="btn p" href="{APP}">Open the live app</a></div></section>

<section id="next"><h2>What's next</h2><ul class="l"><li>Add June and July market-trend data.</li><li>Test floor area and building age.</li><li>Re-check once the hidden August to September adverts are released.</li><li>Dig into waterfront and luxury, where we miss most.</li></ul></section>
</main>
<footer><div><b>Team d4data &middot; Microburbs Hackathon 2026</b><br>Research and data for informational purposes only. Estimates are not valuations and not financial advice. Predictions use only information dated by 31 July 2026. Map data &copy; OpenStreetMap contributors.</div></footer>
</body></html>"""
out = HERE / "index.html"
out.write_text(HTML, encoding="utf-8")
print("wrote", out, f"({out.stat().st_size/1e3:.0f} KB)")
