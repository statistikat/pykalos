# pykalos implementation changes needed

Implementation and tests checked 2026-11-23 with Kalos pinned to `cb5c2de` after the 23-F.4 checkpoint. `src/pykalos` owns the Python API and defaults, `bindings` translates to the C++ request and result, and `vendor` holds the locked core and evidence. Refresh generated sources with `tools/sync-core.py` when adopting core fixes.

## P1 — Validate the Python automatic-fit request before coercion

**Fixed.** The monthly route constructs twelve default MSR filters. Other frequencies receive an empty default and the core returns its existing monthly-only status. The regression test calls the real adapter with the maximum signed 32-bit frequency and inspects the request handed to it. [Request construction](src/pykalos/__init__.py) · [Validation tests](tests/test_request_validation.py)

## P1 — Reject unknown raw keys and negative budgets

**Fixed.** Commits `4b04c75` and `77b7925` hardened the raw parser and its input tests.

The raw entry rejects unknown keys and checks both outlier budgets before conversion to `size_t`. Regression tests cover misspelled keys, negative budgets, and valid requests through both entry points. The pinned core now checks signed annual horizon arithmetic and the combined extended length before estimation. [Raw parser](bindings/module.cpp#L112) · [Budget checks](bindings/module.cpp#L358) · [Regression tests](tests/test_request_validation.py#L270)

## P2 — Make the solver and horizon metadata agree with the pinned core

**Fixed at the M5 checkpoint.** The automatic-fit capability identifies the pinned Levenberg–Marquardt landing and final solver and reports the solver by stage. The horizon field documents nonnegative monthly and negative annual inputs. The installed-wheel tests check a one-year backcast, a two-year forecast and overflow refusals. [Pinned estimator](vendor/kalos/src/x13_automatic.cpp) · [Capability projection](bindings/module.cpp) · [Boundary tests](tests/test_x13_automatic.py)

## P2 — Exercise NumPy and make provider qualification reproducible

**Implemented at the M5 checkpoint.** CI builds with the provider recipe from the exact Kalos revision in the lock and installs the wheel into a fresh environment. The minimal and NumPy jobs check the loaded OpenBLAS version, ABI, binary path and checksum. The NumPy job explicitly imports NumPy before running interoperability and request validation. A local source-archive wheel build passed on macOS ARM64. Hosted Linux results remain pending. [Workflow](.github/workflows/smoke.yml) · [Provider check](tools/check-wheel-provider.py)

## Verification of the current fixes

On macOS ARM64 with Python 3.15 and NumPy 2.5.5, all **65 tests passed** across `test_request_validation`, `test_numpy_interop` and `test_smoke`. The tests used the updated wrapper and compiled extension for the current binding revision. Offline verification of the locked core and evidence also passed.

## Original review checks at `808e01c`

The offline snapshot check and all three smoke tests passed. On macOS ARM64 with Python 3.15 and Homebrew OpenBLAS 0.3.34, full discovery ran 30 tests with four landing-coefficient failures (`ao_nodet`, `mode_logadd`, `mode_mult`, and `mode_pseudo`) and nine NumPy skips. The run used the Homebrew provider build. The subsequent Linux qualification reran all four cases successfully on pinned OpenBLAS 0.3.34 with the existing tolerances. The macOS/Homebrew discrepancy remains open. [Qualification results](IMPLEMENTATION_STATUS.md#L912)
