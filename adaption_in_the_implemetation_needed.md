# pykalos implementation changes needed

Reviewed 2026-11-23 at `808e01c`, with Kalos pinned to `f500162`. `src/pykalos` owns the Python API and defaults, `bindings` translates to the C++ request and result, and `vendor` holds the locked core and evidence. Refresh generated sources with `tools/sync-core.py` when adopting core fixes.

## P1 — Validate the Python automatic-fit request before coercion

A request-capture probe showed that `frequency=12.9` and `start_period=1.9` become `12` and `1`, `forecast=0.9` becomes `0`, the third value of a span is discarded, and `use_calendar_detection="False"` becomes `True`. With the built extension, both a digit string and bytes reached the core as series input. These conversions can change the calendar, remove a requested horizon, or change whether the engine refuses a request. Default seasonal requests are also allocated from the coerced frequency before the core can refuse an unsupported frequency. [Python request construction](src/pykalos/__init__.py#L119)

Check scalar integer fields for exact values and range, flags for boolean values, and spans for exactly two integer endpoints. Reject text, bytes, and non-vector series at the boundary. Preserve supported numeric iterables and NumPy scalar types with an explicit policy, and preserve documented core status responses for valid but unsupported specifications. Only construct per-month defaults after checking the frequency. Add direct tests for each malformed input and a monthly and quarterly request to pin the existing status behavior.

## P1 — Reject unknown raw keys and negative budgets

The built `x13_automatic_fit` extension accepted an extra `use_calender_detection` key and returned the same status as the request without it. The raw parser reads named fields individually, so accidentally misspelled optional options can silently disappear. By inspection, `outlier_max_round` and `outlier_max_outliers` cast a signed `long` to `size_t` without a sign check. [Raw request parser](bindings/module.cpp#L63) · [Raw exported entry point](bindings/module.cpp#L473)

Validate keys against the raw request schema and report unknown names before calling C++. Check the two budgets before unsigned conversion. Keep the raw entry’s explicit sigma contract and the Python convenience entry’s default. Exercise both APIs with a typo, a negative budget, and a valid request. Adopt Kalos’s checked horizon limits on the next core refresh. [Core findings](../kalos/adaption_in_the_implemetation_needed.md)

## P2 — Make the solver and horizon metadata agree with the pinned core

The installed capability dictionary reports `estimation_solver = "bfgs_default"`. The pinned core header describes the `PinnedLevenbergMarquardt` route. The capability dictionary also says horizons are nonnegative month counts, while the Python wrapper and core document that negative values represent counts of annual frequencies. Align these fields with the pinned contract, and extend the capability test to check the actual solver and horizon semantics. [Capability projection](bindings/module.cpp#L424) · [Python horizon documentation](src/pykalos/__init__.py#L93) · [Pinned core header](vendor/kalos/include/kalos/x13_automatic.hpp#L25)

## P2 — Exercise NumPy and make provider qualification reproducible

The smoke workflow installs the wheel without dependencies and has no explicit NumPy installation. The NumPy class skips when NumPy is absent. Install NumPy in a dedicated test lane and run the input-shape, dtype, stride, and read-only buffer assertions there. Keep a minimal dependency lane for the base API. The workflow fetches provider tooling at a separate older Kalos commit. Use the locked provider recipe or an explicit, independently checked tooling pin, and log the actual provider version, build configuration, and library fingerprint from the wheel test environment. [Smoke workflow](.github/workflows/smoke.yml#L8) · [NumPy tests](tests/test_numpy_interop.py#L13) · [Core lock](core.lock.json#L1)

## Review checks

The offline snapshot check and all three smoke tests passed. On macOS ARM64 with Python 3.15 and Homebrew OpenBLAS 0.3.34, full discovery ran 30 tests with four landing-coefficient failures (`ao_nodet`, `mode_logadd`, `mode_mult`, and `mode_pseudo`) and nine NumPy skips. The run used the Homebrew provider build. Repeat the failing cases with the qualification provider and compare the first numerical divergence before changing any tolerances.
