# pykalos implementation changes needed

Implementation and tests checked 2026-11-23 with Kalos pinned to `cb5c2de` after the 23-F.4 checkpoint. `src/pykalos` owns the Python API and defaults, `bindings` translates to the C++ request and result, and `vendor` holds the locked core and evidence. Refresh generated sources with `tools/sync-core.py` when adopting core fixes.
Refreshed 2026-11-27 on Linux at commit `23bef33` (core `6fee68c`); all five review items remain fixed and were re-certified through every subsequent re-pin. The historical verification section is retained as recorded.

## Status refresh (2026-11-27)

The core pin advanced `cb5c2de` → `ec17543` (M10-S3/M11: vendored SLICOT SB03MD closure,
built from source into the wheel with `-ffp-contract=off`) → `6fee68c` (M12: certified
post-pivot diffuse filter). Each re-pin re-certified with the provider gate flipping only
its revision field. Measured effect: the full suite wall dropped ~40% at the SLICOT pin,
and the M12 re-cert reproduced the ratified drift classes (spot airpass θ 1.9e-12,
pinned-LM coefficients ≤2.66e-08, Δadjll 1.28e-12 — all inside class; gaps and k=0 shapes
bit-identical), with the JVM-parity stop gate holding at ≥460× margin and **zero hex
fixtures moved**. One tolerance changed by maintainer ruling (2026-11-26): the
self-consistency coefficient budget 1e-8 → 1e-7 in `test_estimation.py`; the
log-likelihood and jacobian budgets were measured and stay. Suite state: **132 passed /
748 subtests** twice, sensitive-files 14/79, NumPy-free 111/21/720, collection unchanged.

## Remaining items (2026-11-27)

1. **Hosted wheel matrix (the main open item):** every cibuildwheel image now needs a
   Fortran compiler for the vendored SLICOT closure; macOS wheels must bundle/locate
   libgfortran at build time (no direct wheel dependency — the closure compiles to zero
   `_gfortran` references — but `gfortran` must exist, and the pinned provider carries
   libgfortran transitively); a Windows wheel built without a Fortran toolchain runs the
   qualified QR-everywhere state (`KALOS_WITH_SLICOT=OFF`), which the upstream ledger
   documents as the qualified OFF configuration rather than a defect.
2. **Wheel publication** (PyPI index and any additional ABI/platform targets) is a
   maintainer action; local Linux wheels are certified.
3. No open functional items: the M12 re-pin inventory is empty and the standing re-pin
   convention (sync-core → wheel gate → full suite) is the routine for future core
   advances.

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

On macOS ARM64 with Python 3.15 and NumPy 2.5.5, the source-archive wheel passed all **91 tests**, including the full 13-case automatic and four-case horizon replay (**5,640 numerical checks**). Offline verification of the locked core and evidence passed. A separate Homebrew provider wheel passed all four previously failing automatic cases. [Checkpoint qualification](IMPLEMENTATION_STATUS.md#m5-checkpoint-verification-on-macos-arm64)

## Original review checks at `808e01c`

The offline snapshot check and all three smoke tests passed. On macOS ARM64 with Python 3.15 and Homebrew OpenBLAS 0.3.34, full discovery ran 30 tests with four landing-coefficient failures (`ao_nodet`, `mode_logadd`, `mode_mult`, and `mode_pseudo`) and nine NumPy skips. The run used the Homebrew provider build. The subsequent Linux qualification reran all four cases successfully on pinned OpenBLAS 0.3.34 with the existing tolerances. The current checkpoint also passes these four cases on macOS with both provider builds.
