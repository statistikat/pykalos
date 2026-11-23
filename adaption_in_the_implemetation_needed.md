# pykalos implementation changes needed

Implementation and tests checked 2026-11-23 against the working tree based on `5771ce1`, with Kalos pinned to `f500162`. `src/pykalos` owns the Python API and defaults, `bindings` translates to the C++ request and result, and `vendor` holds the locked core and evidence. Refresh generated sources with `tools/sync-core.py` when adopting core fixes.

## P1 — Validate the Python automatic-fit request before coercion

**Fixed.** The monthly route constructs twelve default MSR filters. Other frequencies receive an empty default and the core returns its existing monthly-only status. The regression test calls the real adapter with the maximum signed 32-bit frequency and inspects the request handed to it. [Request construction](src/pykalos/__init__.py) · [Validation tests](tests/test_request_validation.py)

## P1 — Reject unknown raw keys and negative budgets

**Fixed.** Commits `4b04c75` and `77b7925` hardened the raw parser and its input tests.

The raw entry rejects unknown keys and checks both outlier budgets before conversion to `size_t`. Regression tests cover misspelled keys, negative budgets, and valid requests through both entry points. The Kalos horizon arithmetic fix is in the core working tree. This Python revision still vendors the earlier core pin. [Raw parser](bindings/module.cpp#L112) · [Budget checks](bindings/module.cpp#L358) · [Regression tests](tests/test_request_validation.py#L270)

## P2 — Make the solver and horizon metadata agree with the pinned core

**Planned for the next Python core-pin update.** The project records the dependency on the next pin without assigning a numbered milestone. [Deferral record](IMPLEMENTATION_STATUS.md#L949)

The original review overstated the solver mismatch. At the current pin, the outer estimator selects BFGS and the inner stages use the pinned Levenberg–Marquardt solver. The capability text does omit negative annual horizon counts. At the pin update, describe the solver stages used by that revision and test the horizon description against the accepted month and annual-count inputs. [Pinned estimator](vendor/kalos/src/x13_automatic.cpp#L527) · [Pinned contract](vendor/kalos/include/kalos/x13_automatic.hpp#L25) · [Capability projection](bindings/module.cpp#L696)

## P2 — Exercise NumPy and make provider qualification reproducible

**Planned for the next Python core-pin update.** The NumPy CI lane, provider fingerprint, and tooling pin are deferred together. [Deferral record](IMPLEMENTATION_STATUS.md#L958)

The smoke workflow installs the wheel without dependencies and has no explicit NumPy installation. The NumPy class skips when NumPy is absent. Install NumPy in a dedicated test lane and run the input-shape, dtype, stride, and read-only buffer assertions there. Keep a minimal dependency lane for the base API. The workflow fetches provider tooling at a separate older Kalos commit. Use the locked provider recipe or an explicit, independently checked tooling pin, and log the actual provider version, build configuration, and library fingerprint from the wheel test environment. [Smoke workflow](.github/workflows/smoke.yml#L8) · [NumPy tests](tests/test_numpy_interop.py#L13) · [Core lock](core.lock.json#L1)

## Verification of the current fixes

On macOS ARM64 with Python 3.15 and NumPy 2.5.5, all **65 tests passed** across `test_request_validation`, `test_numpy_interop` and `test_smoke`. The tests used the updated wrapper and compiled extension for the current binding revision. Offline verification of the locked core and evidence also passed.

## Original review checks at `808e01c`

The offline snapshot check and all three smoke tests passed. On macOS ARM64 with Python 3.15 and Homebrew OpenBLAS 0.3.34, full discovery ran 30 tests with four landing-coefficient failures (`ao_nodet`, `mode_logadd`, `mode_mult`, and `mode_pseudo`) and nine NumPy skips. The run used the Homebrew provider build. The subsequent Linux qualification reran all four cases successfully on pinned OpenBLAS 0.3.34 with the existing tolerances. The macOS/Homebrew discrepancy remains open. [Qualification results](IMPLEMENTATION_STATUS.md#L912)
