# pykalos

Minimal Python bindings calling [Kalos](https://github.com/statistikat/kalos).
`core_version()`, `capabilities()` and `convolve(left, right)` are the raw
surface; `x13_automatic(series, ...)` runs the qualified automatic-spec X-13
preprocessing pipeline (item 21-H) through the same pinned core.

The TRAMO preprocessing functions use the frozen 23-B contract.
`tramo_critical_value(n)` returns the critical value for an observation count.
`tramo_seasonality(series)` reports Qs, Friedman tests and the differenced series.
`tramo_transform_decision(series, log_preference, precision)` reports the log/level
choice, both branch readouts and the effective seasonal model. The series must
contain at least 24 finite monthly observations. Robust AO/LS pre-correction and
a full TRAMO/SEATS fit remain outside these operations.

For the monthly trading-day F-test, pass the dated observations on their
estimation scale to `tramo_calendar_f_test(series, start_year=1990,
start_month=1, mean=True, significance=0.01, precision=1e-3)`. The result
names the selected effect and reports both candidates' residual sums of
squares, degrees of freedom, mean squares and lower-tail probabilities.
Use `tramo_full_initial_calendar(series, start_year=1990, start_month=1, log=True)`
for the stock initial TRfull rule on original observations. It returns the contrast
comparison and the mean, leap-year and Easter t statistics and retention decisions.
`tramo_residual_trading_days` takes the fitted residuals, the original estimation
start year, start month, length and significance. It returns the late controller's
F statistic, upper-tail probability and decision to refit.

Call `estimate_tramo_tr1(series, start_year=1990, start_month=1)` for stock
TR1 preprocessing of a complete monthly series. Its result gives the fitted
model, regression variables in model order with zero-based outlier positions,
likelihood statistics and dated residuals.

For complete monthly observations, `tramoseats_fit(series, start_year=1990,
start_month=1)` estimates the RSA0 template from the original series. It
returns the fitted airline MA coefficients, mean, likelihood and dated WK
and merged components. Use `fit["finalSA"]`, `fit["finalTrend"]`,
`fit["finalSeasonal"]` and `fit["finalIrregular"]` for the observed period.
`fit["series_forecast_stdev"]` contains the preprocessing model’s original-series
standard errors on `fit["series_forecast_domain"]`; `Series/StdevForecast`
rows contain the independently estimated WK errors.
The preprocessing residuals are in `fit["residuals"]`, with their start year
and month, the residual vector (`tsres`), its standard error (`ser`) and
the 24-lag independence test (`lb`). The test returns `value`, `pvalue`,
`df` and `lags`. Up to 24 residuals give an undefined independence statistic and probability.
The Doornik–Hansen normality test is returned as `doornikhansen` and is
`None` when there are at most seven fitted residuals.
Use `tramoseats_fit(series, template="RSA1", ...)` for the stock transformation
and outlier detection followed by monthly SEATS. The result includes the TR1
preprocessing record, product model-change flag, dated components and
forecasts. `series_forecast_stdev` gives the original-series forecast errors
with fitted drift and outlier uncertainty, including the lognormal scale
conversion on multiplicative fits. Raw RSA1 and standalone TR1 both return the fitted residual scale,
24-lag Ljung–Box test and Doornik–Hansen test. `capabilities()["tramo_seats_fit"]["by_template"]` lists the
qualified uncertainty and residual fields for each template. For RSA1,
`restored_outliers_by_mode` lists the outliers supported by each decomposition
mode. An unsupported fitted outlier raises `ValueError`. `estimate_tramo_tr1`
returns the preprocessing fit independently.

Use `estimate_tramo_tr3(series, start_year=..., start_month=...)` for automatic
monthly TR3 SARIMA identification, or `tramoseats_fit(series, template="RSA3", ...)`
for its SEATS decomposition. Both return the chosen orders, coefficients,
registered effects, likelihood and dated full residuals, including their standard
error, 24-lag independence test and Doornik–Hansen normality test. The
independence test uses the fitted ARMA orders for the degrees of freedom. RSA3 reports its
original-series forecast uncertainty as `unavailable` for a positive horizon.
Model selection outside the supported controller rounds raises `ValueError`.

For a fixed monthly SEATS model, `seats_extract_wk(series, innovation_variance, ...)`
takes the fitted SARIMA coefficients and returns ordered `initial` and `final`
component rows. Each row includes a component, information type, start year,
one-based start month and values. `seats_from_tramo(series, ssq, effective,
estimated, ...)` also restores fitted deterministic effects into `merged`
rows. Supply AO, LS and TC effects as mappings with `type`, zero-based
observation `position` and `coefficient`. TC uses the stock monthly decay
of 0.7 in additive and multiplicative decompositions. Both operations use negative horizons for
years and positive horizons for periods. The default forecast is two years.
Legacy approximation covers the monthly airline retry and the mean-free
(2,1,0)(1,1,0) seasonal re-estimation used in the mixed AO/LS fitted models.

For a fixed quarterly or monthly model, call `x13_fit` with explicit seasonal
filters and Henderson length. The result includes the captured preadjustment
tables, the X-11 tables consumed by the restore, all nine finals and the
seasonally adjusted, trend and irregular components. Supply fixed regression
coefficients and their model-ordered columns when needed.

```python
fit = pykalos.x13_fit(series, frequency=12, start_period=1,
                      seasonal=["s3x9"] * 12, trend_length=13)
adjusted = fit["finalSA"] if fit["available"] else None
```

`capabilities()["restricted_fit"]` describes this route. Unrestricted fitting
remains gated.

```python
import pykalos
pykalos.core_version()
pykalos.convolve([1, -0.4], [1, 0.2])
result = pykalos.x13_automatic(series, start_year=1990, start_period=1)
result["status"]  # "available" or the verbatim fail-closed core status
```

## Local build

Install an LP64 OpenBLAS with CBLAS/LAPACKE development headers (baseline 0.3.34),
a C++17 compiler, CMake and Python 3.10+. Then run `python -m pip install .`.
Set `CMAKE_ARGS="-DOpenBLAS_ROOT=/path/to/openblas"` if discovery needs help.
Core sources are bundled and never fetched during installation. The current
source-built wheel links external OpenBLAS by default. An opt-in POSIX or Windows UCRT64 build
(`-DPYKALOS_BUNDLE_OPENBLAS=ON -DOpenBLAS_ROOT=<pinned-provider>`) links the
LP64 static archive privately into the extension. The portable workflow repairs
Fortran and OpenMP runtime dependencies, installs the wheel in isolation, checks
provider visibility, and exercises both NumPy import orders. Hosted Linux, macOS and Windows qualification is tracked in IMPLEMENTATION_STATUS.md.

Inputs are copied into owned vectors. Computation releases the GIL, and signal
checks reacquire it only on the calling thread. Optional OpenMP is owned by Kalos.
`KALOS_NUM_THREADS` takes precedence over `PERSEPHONE_NUM_THREADS`.

```sh
python tools/sync-core.py --core ../kalos --kind python --revision <commit>
python tools/sync-core.py --verify
python -m unittest discover -s tests
```

Do not edit `vendor/kalos`; refresh the pinned snapshot. See
[implementation status](IMPLEMENTATION_STATUS.md) for this repository's scope.

`prepare_regression(length, start=(year, period), frequency=..., ...)` aligns
named, dated columns to a selected estimation window and its optional backcast
and forecast extensions. Its `design` contains observed columns, coefficients
and fixed flags. `prepare_series(series, transformation="log", degree=...)`
returns the transformed data, an explicit missing mask and the source and local
rows contributing to the likelihood Jacobian. Periods are one-based and row
offsets are zero-based.

`estimate_sarima_fixed(series, period=..., d=..., seasonal_d=..., blocks=...,
control=...)` estimates a fixed SARIMA order. Each supplied `ar`, `ma`,
`seasonal_ar` or `seasonal_ma` block contains `initial` and `fixed` vectors.
Omitted blocks have order zero. The returned coefficient dictionary uses
Kalos AR signs, with polynomial 1−φB, and MA signs with polynomial 1+θB.
Optional `design` accepts the observed design from `prepare_regression`.

Supply all eight control fields. For example, a Zero start with the BFGS
solver uses the following explicit values.

```python
control = dict(eps=1e-7, feps=1e-4, maximum_likelihood=True,
               unit_root_search=False, corrected_degrees_of_freedom=True,
               fast_derivatives=True, starting_point="zero", solver="bfgs")
fit = pykalos.estimate_sarima_fixed(
    values, period=12, d=1, seasonal_d=1, control=control,
    blocks={"ma": {"initial": [0.0], "fixed": [False]},
            "seasonal_ma": {"initial": [0.0], "fixed": [False]}})
```

The other start names are `default`, `hannan_rissanen` and `multiple`.
The `pinned_levenberg_marquardt` solver accepts the core's fully free block
envelope. Control decisions, pass likelihoods, evaluation counts and the
retained coefficients are available even when the optimizer reports a
non-converged point.
