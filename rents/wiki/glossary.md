# Glossary

- **G-NAF**: Geocoded National Address File; official Australian address database. Ids like `GANSW705970502`.
- **SAL**: ABS "Suburb and Locality"; the exact suburb naming the API requires (e.g. `Glebe (NSW)`).
- **ABS mesh block (MB)**: smallest ABS geographic unit (a few dozen homes in dense areas); 11-digit code; each address is in exactly one.
- **LGA**: Local Government Area (here, the City of Sydney). **SA4**: ABS statistical area level 4.
- **Advert / listing**: a rental advertisement with weekly rent, date, beds, baths, car spaces.
- **Held-out / check pile**: adverts not used for building or tuning, only for measuring accuracy.
- **Build pile**: earlier adverts used to fit and tune the model.
- **Median absolute error**: median of |predicted - actual| in dollars per week; the ranking metric.
- **Within $100**: share of predictions whose absolute error is at most $100; the tie-breaker.
- **R squared**: 1 - (sum of squared model errors / sum of squared errors of always predicting the mean); share of rent variation explained.
- **Leakage**: using information from after the cutoff (or from the check set) when building; forbidden here.
- **Cutoff**: 31 July 2026.
- **LightGBM / XGBoost**: gradient-boosted tree libraries.
- **SHAP**: method that splits each prediction into per-feature contributions (exact for trees).
- **Huber / L1 objective**: training losses that are less sensitive to outliers / match absolute error.
- **AVM**: automated valuation model (sale value estimate from the API).
- **Heat map**: map coloured by rent level (planned with Leaflet + OpenStreetMap).
