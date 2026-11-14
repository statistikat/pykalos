# pykalos

Minimal Python bindings calling [Kalos](https://github.com/statistikat/kalos).
This initial structure deliberately exposes only `core_version()`,
`capabilities()` and `convolve(left, right)`. It does not expose model fitting,
R API parity or full seasonal adjustment.

```python
import pykalos
pykalos.core_version()
pykalos.convolve([1, -0.4], [1, 0.2])
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
