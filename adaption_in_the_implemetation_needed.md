# pykalos implementation changes needed

Status checked 2026-11-23 at `8c4eea5`, with Kalos pinned to `f500162`. `src/pykalos` owns the Python API and defaults, `bindings` translates to the C++ request and result, and `vendor` holds the locked core and evidence. Refresh generated sources with `tools/sync-core.py` when adopting core fixes.

## P1 — Validate the Python automatic-fit request before coercion

**Partially fixed; needs work now.** The targeted request-validation tests passed locally (42 passed and 10 NumPy-dependent tests skipped).

The wrapper now rejects fractional integer fields, non-boolean flags, malformed spans, text, and multivariate input. The remaining issue is the seasonal default: a probe with unsupported `frequency=97` still constructed 97 entries before the core returned its monthly-only status. Avoid allocation proportional to an unsupported frequency while preserving that status. Add a test that checks the constructed request size. [Request construction](src/pykalos/__init__.py#L337) · [Regression tests](tests/test_request_validation.py#L53)

## P1 — Reject unknown raw keys and negative budgets

**Fixed.** Commits `4b04c75` and `77b7925` hardened the raw parser and its input tests.

The raw entry rejects unknown keys and checks both outlier budgets before conversion to `size_t`. Regression tests cover misspelled keys, negative budgets, and valid requests through both entry points. Checked horizon arithmetic remains a separate Kalos finding. [Raw parser](bindings/module.cpp#L112) · [Budget checks](bindings/module.cpp#L358) · [Regression tests](tests/test_request_validation.py#L270)

## P2 — Make the solver and horizon metadata agree with the pinned core

**Planned for the next Python core-pin update.** The project records the dependency on the next pin without assigning a numbered milestone. [Deferral record](IMPLEMENTATION_STATUS.md#L949)

The original review overstated the solver mismatch. At the current pin, the outer estimator selects BFGS and the inner stages use the pinned Levenberg–Marquardt solver. The capability text does omit negative annual horizon counts. At the pin update, describe the solver stages used by that revision and test the horizon description against the accepted month and annual-count inputs. [Pinned estimator](vendor/kalos/src/x13_automatic.cpp#L527) · [Pinned contract](vendor/kalos/include/kalos/x13_automatic.hpp#L25) · [Capability projection](bindings/module.cpp#L696)

## P2 — Exercise NumPy and make provider qualification reproducible

**Planned for the next Python core-pin update.** The NumPy CI lane, provider fingerprint, and tooling pin are deferred together. [Deferral record](IMPLEMENTATION_STATUS.md#L958)

The smoke workflow installs the wheel without dependencies and has no explicit NumPy installation. The NumPy class skips when NumPy is absent. Install NumPy in a dedicated test lane and run the input-shape, dtype, stride, and read-only buffer assertions there. Keep a minimal dependency lane for the base API. The workflow fetches provider tooling at a separate older Kalos commit. Use the locked provider recipe or an explicit, independently checked tooling pin, and log the actual provider version, build configuration, and library fingerprint from the wheel test environment. [Smoke workflow](.github/workflows/smoke.yml#L8) · [NumPy tests](tests/test_numpy_interop.py#L13) · [Core lock](core.lock.json#L1)

## Original review checks at `808e01c`

The offline snapshot check and all three smoke tests passed. On macOS ARM64 with Python 3.15 and Homebrew OpenBLAS 0.3.34, full discovery ran 30 tests with four landing-coefficient failures (`ao_nodet`, `mode_logadd`, `mode_mult`, and `mode_pseudo`) and nine NumPy skips. The run used the Homebrew provider build. The subsequent Linux qualification reran all four cases successfully on pinned OpenBLAS 0.3.34 with the existing tolerances. The macOS/Homebrew discrepancy remains open. [Qualification results](IMPLEMENTATION_STATUS.md#L912)
