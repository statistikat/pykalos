# pykalos

Minimal Python bindings calling [Kalos](https://github.com/statistikat/kalos).
`core_version()`, `capabilities()` and `convolve(left, right)` are the raw
surface; `x13_automatic(series, ...)` runs the qualified automatic-spec X-13
preprocessing pipeline (item 21-H) through the same pinned core. Unrestricted
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
local wheel links the external OpenBLAS installation; portable bundled wheels,
private provider symbol isolation and NumPy interoperability qualification are
future distribution work, not claimed by this minimal scaffold.

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
