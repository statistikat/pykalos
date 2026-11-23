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

For complete monthly observations, `tramoseats_fit(series, start_year=1990,
start_month=1)` estimates the RSA0 template from the original series. It
returns the fitted airline MA coefficients, mean, likelihood and dated WK
and merged components. Use `fit["finalSA"]`, `fit["finalTrend"]`,
`fit["finalSeasonal"]` and `fit["finalIrregular"]` for the observed period.
`fit["series_forecast_stdev"]` contains the preprocessing model’s original-series
standard errors on `fit["series_forecast_domain"]`; `Series/StdevForecast`
rows contain the independently estimated WK errors.
The preprocessing residuals are in `fit["residuals"]`, with their start year
and month, the residual vector (`tsres`) and its standard error (`ser`).
The supported template and approximation boundary are reported by
`capabilities()["tramo_seats_fit"]`.

For a fixed monthly SEATS model, `seats_extract_wk(series, innovation_variance, ...)`
takes the fitted SARIMA coefficients and returns ordered `initial` and `final`
component rows. Each row includes a component, information type, start year,
one-based start month and values. `seats_from_tramo(series, ssq, effective,
estimated, ...)` also restores fitted deterministic effects into `merged`
rows. Supply AO/LS effects as mappings with `type`, zero-based observation
`position` and `coefficient`. Both operations use negative horizons for
years and positive horizons for periods. The default forecast is two years.

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
