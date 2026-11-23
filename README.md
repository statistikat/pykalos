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

Unrestricted
fitting, the restricted fixed-coefficient fit and R API parity are not
exposed here.

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
source-built wheel links external OpenBLAS. The NumPy test lane exercises array
inputs and both library import orders. Portable wheels with private OpenBLAS
remain a distribution milestone.

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
