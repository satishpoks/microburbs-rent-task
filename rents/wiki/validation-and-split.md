# Validation, date split, tuning rules

## The rule (strict reading)
"Use earlier adverts to build your estimate. Check it against later adverts dated by 31 July 2026. Never use those later adverts while building or tuning your method."
=> The **check pile is for checking only**: do not train on it, do not choose hyperparameters or features by looking at its score. (An earlier Claude suggestion "don't overtune on the holdout" was too soft - corrected.)

## Split design
- **Time split, not random** (random leaks the future and hides rent drift).
- Suggested: build pile = adverts before **1 Jun 2026**; check pile = **1 Jun - 31 Jul 2026**. Adjust so the check pile has at least a few thousand adverts for a stable median (widen the window if thin, keep it strictly later than the build pile). The real test is ~1 day after the cutoff and runs two months (Aug-Sep), so a recent-weeks check mimics it.
- The report must state the exact cut-off date used.
- **Tune only inside the build pile** with rolling date splits (train up to month X, validate on X+1, repeat); pick settings by average score; look at the spread across folds (high spread = unstable model). Touch the check pile ONCE at the end, then record the numbers.

## Metrics to report
- **Median absolute error ($/week)** - the ranking metric.
- **Share within $100** - the tie-breaker.
- **R squared** = 1 - SS_residual / SS_total (share of variation in weekly rent explained; 1 perfect, 0 = no better than predicting the mean). Report on the check pile.
- Compare against the $86 / 55.21% baseline and against your own suburb-median baseline.

## Open ambiguity: retraining on the check pile
After measuring accuracy, may we retrain on the 1 Jun - 31 Jul adverts before predicting Aug-Sep? Wording ("never use those later adverts while building or tuning") suggests NO. Safe default: do not retrain on the check pile; ask organisers. If allowed, retraining on all data <= 31 Jul usually helps (most recent rents). Decide BEFORE 13:45 and state it in the report.

## "Test" clarified
Own check = up to 31 Jul only. Official test = hidden 1 Aug - 30 Sep adverts. Nothing after 31 Jul in any step, including features such as AVM dates, suburb series, vacancy/yield series.
