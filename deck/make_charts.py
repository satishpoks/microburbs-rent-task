"""Chart images for the demo deck (PNG, 16:9-friendly). Aggregate numbers only.
Run: python deck/make_charts.py"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent          # repo root (results/, landing/, submission/ ...)
OUT = HERE / "img"
OUT.mkdir(exist_ok=True)
NAVY, BLUE, GREY, PALE, MUT = "#14233C", "#2A78D6", "#C4C3B7", "#F4F3EE", "#5b6a80"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 14, "axes.edgecolor": MUT, "axes.labelcolor": NAVY, "text.color": NAVY, "xtick.color": MUT, "ytick.color": MUT})
TREND = json.load(open(ROOT / "results" / "trend_rows.json"))
M = json.load(open(ROOT / "results" / "metrics.json"))
FI = ROOT / "results" / "feature_impact.csv"


def clean(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def save(fig, name):
    fig.savefig(OUT / name, dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote", name)


# 1. rent index
fig, ax = plt.subplots(figsize=(11, 5.2))
xs = [r["x"] for r in TREND]
ax.axhline(100, color=MUT, ls="--", lw=1)
for a, b, lab, ha, xt in [(2020.17, 2020.42, "COVID", "left", 2020.17), (2021.92, 2022.17, "Borders reopen", "right", 2022.17), (2022.33, 2023.85, "Rate hikes", "left", 2022.33)]:
    ax.axvspan(a, b, color=GREY, alpha=0.35, lw=0)
    ax.text(xt, 139 if lab == "Borders reopen" else 144, lab, fontsize=10, color=MUT, va="top", ha=ha)
ax.plot(xs, [r["raw"] for r in TREND], color=GREY, lw=2, label="Raw median")
ax.plot(xs, [r["adj"] for r in TREND], color=BLUE, lw=3.2, label="Mix-adjusted index")
low = min(TREND, key=lambda r: r["adj"]); last = TREND[-1]
ax.scatter([low["x"]], [low["adj"]], color=BLUE, zorder=5); ax.annotate(f"Low {low['adj']:.1f} (late 2020)", (low["x"], low["adj"]), xytext=(2016.4, 84.5), fontsize=11, color=NAVY, arrowprops=dict(arrowstyle="-", color=MUT, lw=1))
ax.scatter([last["x"]], [last["adj"]], color=BLUE, zorder=5); ax.annotate(f"{last['adj']:.0f}\n(Jul 2026)", (last["x"], last["adj"]), xytext=(last["x"] - 0.9, last["adj"] - 15), fontsize=11, color=BLUE, fontweight="bold")
ax.text(2015.1, 101.5, "2019 average = 100", fontsize=10, color=MUT)
ax.set_ylim(78, 145); ax.set_xlim(2015, 2026.8); clean(ax); ax.set_ylabel("Rent index (2019 = 100)"); ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(0.03, 0.92))
ax.set_title("Rents fell 17%, rose 48% from the low, and sit 32% above 2019", loc="left", fontsize=17, fontweight="bold", color=NAVY, pad=14)
save(fig, "rent_index.png")

# 2. car premium
fig, ax = plt.subplots(figsize=(8, 5))
labs, vals = ["Pre-COVID", "COVID", "Reopening", "2024 on"], [-5, 10, 23, 60]
bars = ax.bar(labs, vals, color=[GREY, GREY, GREY, BLUE], width=0.55)
for b, v in zip(bars, vals):
    ax.text(b.get_x() + b.get_width() / 2, v + (3 if v >= 0 else -9), ("-" if v < 0 else "") + f"${abs(v)}", ha="center", fontweight="bold", fontsize=16)
ax.axhline(0, color=MUT, lw=1); clean(ax); ax.set_ylabel("$ a week"); ax.set_ylim(-18, 72)
ax.set_title("A car space now adds about $60 a week", loc="left", fontsize=17, fontweight="bold", pad=14)
save(fig, "car_premium.png")

# 3. factor groups
import pandas as pd
F = pd.read_csv(FI, index_col=0); F.columns = ["gain", "shap", "logpts", "swing"]
G = {"Market level and momentum": ["level_lag", "level_n", "mom3", "mom6", "mom_city6", "growth_est", "level_prev"],
     "Flat's own rent history": ["prev_lr", "adj_prev", "prev_gap", "prev_cnt", "own_nrm", "own_nrm_n"],
     "Building premium": ["bldg_rel", "bldg_n", "b_same_nrm", "b_same_n", "b_any_nrm", "b_any_n"],
     "Flat size and type": ["bedrooms", "bathrooms", "beds_x_baths", "baths_per_bed", "prop"],
     "Neighbourhood premium": [i for i in F.index if i.startswith("nb")], "Parking": ["car"],
     "Suburb and coordinates": ["suburb", "lat", "lng"], "Building and block context": ["floor_level", "flats_in_building", "block_homes_2026", "block_new_homes_2021_2026"]}
grp = sorted(((k, float(F.loc[[i for i in v if i in F.index], "shap"].sum())) for k, v in G.items()), key=lambda t: t[1])
fig, ax = plt.subplots(figsize=(10, 5.4))
bars = ax.barh([k for k, _ in grp], [v for _, v in grp], color=[BLUE if k == "Market level and momentum" else GREY for k, _ in grp], height=0.62)
for b, (_, v) in zip(bars, grp):
    ax.text(v + 0.8, b.get_y() + b.get_height() / 2, f"{v:.1f}%", va="center", fontweight="bold")
clean(ax); ax.set_xlim(0, 56); ax.set_xlabel("Share of model impact (%)")
ax.set_title("Almost half of each prediction is where the market is right now", loc="left", fontsize=16, fontweight="bold", pad=14)
save(fig, "factors.png")

# 4. model comparison
fig, ax = plt.subplots(figsize=(9, 4.6))
names = ["Median baseline\n(suburb x bedrooms)", "LightGBM v1", "LightGBM v2\n(submitted)"]
meds = [M["baseline_median"]["median_abs_error"], M["lightgbm_v1"]["median_abs_error"], M["lightgbm_v2"]["median_abs_error"]]
w100 = [M["baseline_median"]["within_100"] * 100, M["lightgbm_v1"]["within_100"] * 100, M["lightgbm_v2"]["within_100"] * 100]
bars = ax.barh(names[::-1], meds[::-1], color=[BLUE, GREY, GREY], height=0.55)
for b, m, w in zip(bars, meds[::-1], w100[::-1]):
    ax.text(m + 1.5, b.get_y() + b.get_height() / 2, f"\${m:.1f}   |   {w:.1f}% within \$100", va="center", fontweight="bold", fontsize=13)
clean(ax); ax.set_xlim(0, 150); ax.set_xlabel("Typical weekly miss, $ (shorter is better)")
ax.set_title("Typical miss: $44 a week on adverts the model never saw", loc="left", fontsize=16, fontweight="bold", pad=14)
save(fig, "model_compare.png")

# 5. date split
fig, ax = plt.subplots(figsize=(11, 3.2))
ax.set_xlim(0, 100); ax.set_ylim(0, 10); ax.axis("off")
for x, w, col, ec, ls, t1, t2, tc in [(1, 44, "#4d6c8f", "none", "-", "BUILD", "Before 1 June 2026 | 106,888 adverts\nAll training and tuning", "white"),
                                      (47, 26, BLUE, "none", "-", "CHECK", "1 Jun to 31 Jul 2026\n2,713 adverts\nscored once", "white"),
                                      (75, 24, "white", MUT, "--", "JUDGED", "1 Aug to 30 Sep 2026\n1,699 frozen adverts\nnever seen", NAVY)]:
    ax.add_patch(FancyBboxPatch((x, 2.2), w, 5.2, boxstyle="round,pad=0.1,rounding_size=0.8", fc=col, ec=ec, ls=ls, lw=2))
    ax.text(x + w / 2, 6.0, t1, ha="center", va="center", fontsize=17, fontweight="bold", color=tc)
    ax.text(x + w / 2, 3.6, t2, ha="center", va="center", fontsize=11, color=tc, linespacing=1.4)
ax.text(1, 9.2, "Time", fontsize=11, color=MUT); ax.annotate("", xy=(99, 8.8), xytext=(7, 8.8), arrowprops=dict(arrowstyle="->", color=MUT))
ax.text(50, 0.6, "Nothing dated after 31 July 2026 is used anywhere", ha="center", fontsize=13, color=NAVY, fontweight="bold")
save(fig, "date_split.png")

# 6. momentum windows
fig, ax = plt.subplots(figsize=(11, 4.2))
ax.set_xlim(0, 13); ax.set_ylim(0, 6); ax.axis("off")
months = ["Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep"]
cols = ["#a9c4e0"] * 3 + ["#6b8cab"] * 3 + [BLUE] * 3 + ["white"] * 2 + ["#d7e5f4"] * 2
for i, (m, c) in enumerate(zip(months, cols)):
    ax.add_patch(Rectangle((i + 0.04, 3.7), 0.92, 0.9, fc=c, ec=MUT if c == "white" else "none", ls="--" if c == "white" else "-"))
    ax.text(i + 0.5, 4.15, m, ha="center", va="center", fontsize=12, color="white" if c in (BLUE, "#6b8cab") else NAVY, fontweight="bold")
for x0, n, t in [(0, 3, "6 months back"), (3, 3, "3 months back"), (6, 3, "Latest = market level"), (9, 2, "No data used"), (11, 2, "Judged adverts")]:
    ax.text(x0 + n / 2, 3.25, t, ha="center", fontsize=11)
ax.text(0, 5.0, "Sep 2025", fontsize=10, color=MUT); ax.text(9, 5.0, "data ends 31 May 2026", ha="right", fontsize=10, color=MUT); ax.text(13, 5.0, "Aug-Sep 2026", ha="right", fontsize=10, color=MUT)
for x0, x1, y, t in [(4.5, 7.5, 2.3, "3-month momentum = latest level - level 3 months back"), (1.5, 7.5, 1.1, "6-month momentum = latest level - level 6 months back")]:
    ax.plot([x0, x0, x1, x1], [y + 0.45, y, y, y + 0.45], color=MUT, lw=1.6)
    ax.text((x0 + x1) / 2, y - 0.55, t, ha="center", fontsize=12)
save(fig, "momentum.png")
