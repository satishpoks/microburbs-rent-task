# d4data: Sydney flat rent estimates (Microburbs Hackathon, Rents task)

We estimate weekly rent for all **65,777 City of Sydney flats**, **with and without a car space**.

| Result on our own check (2,713 adverts, 1 Jun - 31 Jul 2026, never used for building) | d4data | Organisers' baseline |
| --- | --- | --- |
| Median absolute error | **$44 / week** | $86 |
| Estimates within $100 | **79.2%** | 55.2% |
| R squared | **0.888** | n/a |

The official score comes from the organisers' hidden 1 Aug - 30 Sep 2026 adverts.

## Where to look (start here, judges)

| What | Where |
| --- | --- |
| **Predictions** (`gnaf_id, rent_with_car_space, rent_without_car_space`; 65,777 unique ids, no blanks) | [`submission/rents_d4data.csv`](submission/rents_d4data.csv) |
| **Report**: insights first, then held-out error, within $100, R squared, the date split, data and method | [`submission/report.html`](submission/report.html) (open in a browser; one self-contained page) |
| **Live app**: look up any flat, describe a property, rent heat map on OpenStreetMap | https://d4data-rent-estimator.vercel.app/ (source in [`app/`](app/)) |
| One-page summary / pitch | [`landing/index.html`](landing/index.html) |
| Code that produced everything, in run order | [`src/`](src/) |
| Metrics and numbers behind the report | [`results/`](results/) |

## Method in short

1. **Clean** (`src/01_flag_leases.py`): 2,785 of 112,457 past adverts removed as errors (impossible bedroom/bathroom counts, rents far from their suburb x bedrooms x year median, exact duplicates).
2. **Baseline** (`src/02_baseline.py`): median rent by suburb x bedrooms x bathrooms, with fallbacks. It is the safety answer so no flat is ever blank.
3. **Model** (`src/03_model_v2.py`): LightGBM on log weekly rent (L1 loss), recent adverts weighted more (half-life 3 years). 40 features in five groups: flat attributes, suburb market level and momentum, the flat's own rent history, building premium over market, and neighbour (250 m / 500 m) premiums. The model predicts each flat twice (car space 1 and 0); with-car is never below without-car.
4. **Honest timing**: every market and history feature is read as it stood 3 months before the advert date, because the hidden adverts fall 2-4 months after our last advert.
5. **Check** (date split, not random): adverts **before 1 Jun 2026 built** the model; adverts **1 Jun - 31 Jul 2026 checked** it once. Settings were chosen on Apr-May 2026 *inside* the build pile and never tuned on the check pile. Nothing dated after **31 Jul 2026** is used anywhere.

Top drivers (share of impact, mean |SHAP|): recent suburb x bedroom market rent 39.6%, the flat's own last rent grown by the market 7.5%, the building's premium over market 5.3%. Full table and charts are in the report.

## Data sources

| Source | Content | Use |
| --- | --- | --- |
| `rents-past-leases-city-of-sydney.csv` (supplied by the organisers, private) | 112,457 adverts for 52,296 flats, Jan 2012 - 31 Jul 2026: weekly rent, listing date, bedrooms, bathrooms, parking, type, coordinates | Training target and history features |
| `rents-input-flats-city-of-sydney.csv` (supplied, public) | The 65,777 flats to predict (33 suburbs): address, coordinates, type, bedrooms, bathrooms, parking, floor, flats in building, block home counts | Flats we predict and their attributes |
| `blocks-homes-and-people-2021-2026.csv` (supplied, private) | 2021 Census and 2026 estimates of homes and people per ABS mesh block | Two columns (homes in 2026, new homes 2021-2026) are model inputs; the rest was tested and did not help |
| Derived by us | Suburb x bedroom market level and momentum, each flat's rent history, building and neighbour premiums | Computed only from adverts dated before the flat's advert date minus 3 months, and never after 31 Jul 2026 |

**No outside data feeds the predictions.** We reviewed the Microburbs Hackathon API (https://api-ht.microburbs.com.au/docs), the Geoscape G-NAF address file and the flat-sales files, but did not use them in the final model (the API returns adverts after the cutoff unless filtered, so it carries leakage risk). The `listings/for-rent` endpoint was never used. The three supplied files are private and day-of only, so they are **not in this repository** (see below).

## Repository layout

```
submission/   rents_d4data.csv, report.html        <- the two deliverables
src/          numbered pipeline scripts (01..08), report_sections.py, experiments/
results/      metrics.json, report_stats.json, feature_impact.csv, report chart inputs
app/          static Rent Estimator (HTML/JS, deployed on Vercel)
landing/      one-page summary (index.html + screenshots)
data/         YOU provide the supplied CSVs here (git-ignored, not published)
```

`src/experiments/` holds side studies that did not change the submission: an ensemble of 15 LightGBM fits (not promoted by the pre-set rule), neighbour-feature ablations and error analysis.

## Reproduce

Python 3.11+ with `pandas numpy lightgbm scikit-learn shap`. Put the three supplied CSVs in `data/` (same file names), then from the repo root:

```bash
python src/01_flag_leases.py     # data/leases_flagged.csv
python src/03_model_v2.py        # runs 02_baseline.py first; writes submission/rents_d4data.csv + results/metrics.json (~5 min)
python src/04_feature_impact.py  # results/feature_impact.csv (SHAP on recent build-pile adverts)
python src/05_report_stats.py    # results/report_stats.json (aggregates only, no per-advert rows)
python src/06_build_report.py    # submission/report.html
python src/08_build_app_data.py  # app/data.js (predictions only)
python src/07_build_landing.py   # landing/index.html (optional)
```

Runs are deterministic (fixed seeds). `src/02_baseline.py` also supports `OUT_SUBDIR=<name>` to run an experiment (e.g. another split date) into `results/<name>/` without touching the submission file.

## Rules we followed

- Only information dated by **31 Jul 2026**; later adverts never used to build, tune or check; `listings/for-rent` never used.
- The check pile was scored once and never used for fitting or tuning.
- No blank answers: every flat has both predictions (baseline fallback), with-car >= without-car.
- Private supplied files and API keys are not committed (`.gitignore`).

Team **d4data**. Licence: MIT (see `LICENSE`).
