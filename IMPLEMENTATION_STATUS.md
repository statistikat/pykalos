# pykalos implementation status

Current Python operations at the 2026-11-23 checkpoint include convolution, dated regression and transformation preparation, explicit fixed-order SARIMA estimation, fixed-coefficient and automatic X-13, TRAMO seasonality, transform and monthly calendar preprocessing decisions, fixed WK extraction, fitted-model decomposition and ordinary monthly RSA0 fitting with forecast errors and residual diagnostics. The dated entries retain the earlier qualification results.

## M5 checkpoint after the TRAMO preprocessing assembly (2026-11-23)

The Python snapshot advances from `f500162` to `cb5c2de193c2cd7e2035a9a99f205186a90a4dec`. This includes the completed 23-F.4 TRAMO preprocessing assembly and the subsequent standalone build, provider selection and checked X-13 horizon changes. At this initial sync, Python exposed convolution and automatic monthly X-13. The 23-F request takes kernel and seam witnesses. A product TRAMO/SEATS binding depends on the assembled decomposition and end-to-end oracle.

The integration gate checks the allowlist, builds and imports the wheel with checksum-pinned OpenBLAS and replays the existing 13 automatic and four horizon cases. Upstream manifest verification covered 187 core, 112 fixture and 331 evidence files. `tools/sync-core.py --verify` verified 143 core files and 11 evidence files before export, and 188 core files (including the generated revision header) and the same 11 evidence files afterwards. The installed wheel reports the exact revision and LP64 OpenBLAS 0.3.34 on macOS ARM64.

### Python automatic-fit capability and horizon contract

The landing and final estimates use the pinned Levenberg–Marquardt solver at this revision. The capability also identifies the differencing and initial ARMA solver and the BFGS transform and outlier requests. The two signed horizon fields now document both monthly and annual inputs. The Python boundary checks their normalized values, extended output length and the core’s refusal of annual multiplication or combined-length overflow. All 72 automatic-boundary, corpus-shape, request-validation, NumPy and smoke tests passed on the installed checkpoint wheel with Python 3.15 and NumPy 2.5.5.

### Installed-wheel provider and NumPy CI

CI reads the core tooling revision from `core.lock.json`. The minimal and NumPy jobs install the built wheel into clean environments. Both log the exact binary mapped behind the extension’s OpenBLAS configuration symbol, its SHA-256, the runtime configuration, integer width and pinned source-archive digest. The NumPy job imports NumPy explicitly and exercises input shapes, strides, dtypes and read-only buffers.

The wheel now uses the vendored core’s provider finder and link probes. A single CMake build directory accepted the qualified root, rejected a missing root and accepted the restored root. The source archive built an installed wheel against the checksum-pinned OpenBLAS 0.3.34. Its runtime configuration on this host was `OpenBLAS 0.3.34 DYNAMIC_ARCH NO_AFFINITY USE_LOCKING neoversen1 SINGLE_THREADED`, with a 32-bit integer ABI and binary SHA-256 `6227c1b96aa62ec2aa7317912cb980ee32dae9adccebc81c105f479482d505e6`. The checker also rejected an unrelated prefix. The three dependency-free smoke tests passed. The workflow YAML parsed locally. Hosted jobs and portable bundled wheels remain outside this local evidence.

### M5 checkpoint verification on macOS ARM64

The final installed wheel built from the source archive passed all **91 tests**, with NumPy installed and all 13 automatic and four horizon cases selected. The numerical replay made **4,353 automatic and 1,287 horizon checks**, with zero failures against the existing decisions and tolerances. At `multi/diff0/tmean` the relative error was **1.619e-4** against Python’s 1e-3 limit. Upstream’s Linux core record at this revision reports 3.1e-3 on that comparison under its 5e-3 limit. Full Linux Python corpus qualification remains open. [Upstream acceptance record](https://github.com/statistikat/kalos/blob/cb5c2de193c2cd7e2035a9a99f205186a90a4dec/tests/test_x13_automatic_oracle.cpp#L211)

On this same host, the old `f500162` wheel failed `ao_nodet` and all three forced-mode landing-coefficient comparisons with checksum-pinned OpenBLAS. The new pin passed all four with that provider and passed **1,324/1,324** checks in a separate Homebrew OpenBLAS 0.3.34 wheel build. The Homebrew binary SHA-256 was `07bc71aac2823e9202ea4088429a4f5d05146aded15e8aa44600e285eb700415`. These runs close the earlier macOS discrepancy for this checkpoint.

### M5 TRAMO preprocessing evidence checkpoint

At the existing core pin `cb5c2de`, the Python evidence allowlist now includes the frozen 23-B transform corpus. The export added six evidence files, bringing the offline-verified totals to 188 core files and 17 evidence files. The Python acceptance gate is a replay of all 29 captured cases, including robust pre-correction refusals, plus checks of shape, frequency, ownership and capability reporting.

### M5 Python TRAMO critical value, seasonality and transform decision

The installed wheel exports `tramo_critical_value`, `tramo_seasonality` and `tramo_transform_decision` and lists all three in `capabilities()["primitives"]`. Python owns and validates the request data before the C++ decision runs with the GIL released. The monthly seasonality and transform operations require at least 24 finite observations. Both report the captured seasonality fields. Disabling detection yields `None` for the nested report. Robust AO/LS pre-correction is refused explicitly. The unrestricted fit gate remains false.

All 29 frozen cases passed on macOS ARM64 with the installed wheel and checksum-pinned OpenBLAS 0.3.34. They cover ten critical-value grid points, five detector series, ten transform decisions and four robust refusals. The replay compares the available floating-point fields and differenced observations at binary64 precision, including signed zero, and checks NaN classification. Shape, scalar, frequency, oversize, ownership and capability checks passed. [Python replay](tests/test_tramo_transform.py)

### M6 NumPy and Kalos provider coexistence

A subprocess regression now loads NumPy before pykalos and then pykalos before NumPy in a fresh interpreter. Each library runs a numerical operation before and after the second import. NumPy solves a linear system. Kalos checks the frozen `tr_gs` transform choice and binary64 log, level and correction values. Both final outputs and the reported provider configuration must agree across orders. The hosted NumPy lane runs this regression and the TRAMO corpus. [Import-order test](tests/test_provider_import_order.py) · [Workflow](.github/workflows/smoke.yml)

On macOS ARM64, the OpenBLAS 0.3.34 wheel and NumPy 2.5.5 (Apple Accelerate) passed both import orders. All 68 NumPy-lane tests passed. In an environment without NumPy, the smoke and TRAMO tests passed and the coexistence test skipped. This verifies the external-provider wheel on this host. Bundling and hosted Linux wheel qualification remain open.

The 23-B source-archive wheel passed all 93 tests present at build time, including the 13 automatic and four horizon X-13 cases (5,640 numerical checks). A second installed wheel linked to Homebrew OpenBLAS 0.3.34 passed the entire 29-case TRAMO fixture and both NumPy import orders. The added oversize refusal also passed on the final wheel. The offline verifier confirmed the 188 core and 17 evidence files.

### M3 Python restricted-fit evidence checkpoint

At core `cb5c2de`, the export allowlist now includes the seven allocation-seam and eleven end-to-end X-13 fit cases. The gate for the public fixed-coefficient fit is the complete quarterly and monthly fixed-route corpus, the out-of-domain horizon cases, the `x13_fast` reference and the core’s exact versus transcendental table thresholds.

### M3 Python restricted fixed-coefficient X-13 fit

`pykalos.x13_fit` accepts complete quarterly or monthly series, fixed regressors and coefficients, one seasonal request per period and an explicit Henderson length. It echoes the effective mode and request provenance, returns all 27 reference tables and the three restored components on success, and preserves the core’s named refusals for MSR or default seasonal filters, automatic trend length and nonzero horizons. The default sigma policy is legacy. The dedicated `restricted_fit` capability reports the fixed-coefficient, fixed-filter and zero-horizon envelope; unrestricted `fit` remains false. [API and example](README.md) · [Core contract](https://github.com/statistikat/kalos/blob/cb5c2de193c2cd7e2035a9a99f205186a90a4dec/docs/contracts/x13-fit-contract.md)

At thread settings 1, 2 and 8 the installed wheel passed all 16 fixed runs across the allocation and fit corpora and both out-of-envelope horizon cases. Each run of the suite compared **44,712 table values** and the exact final-component triplets. Non-log outputs and `a1` were bit-exact. Log-model outputs met the pinned 1e-15 preadjustment, 1e-12 results and 1e-9 finals thresholds. The fourteen directly captured `x13_fast` tables (1,344 values) also matched. Shape, policy, field and integer-range refusals passed. Offline verification covered 188 core and 34 evidence files. [Python oracle replay](tests/test_x13_fixed.py)

Both public X-13 fits now use Python’s integer-index protocol for integer fields. An object whose `__index__` returned a fractional value was previously truncated. The regression failed on the preceding wheel and passed after the correction. All 71 targeted validation, fixed-fit, TRAMO, smoke and NumPy-provider tests passed on the updated installed wheel.

The source archive containing the fixed-fit entry built a wheel and passed **96/96** tests, including all automatic and horizon X-13 corpus cases (5,640 numerical checks), the fixed-fit and TRAMO corpora and both NumPy import orders. The separate 71-test run above covers the subsequent integer-protocol correction. Hosted results are tracked separately from these macOS ARM64 runs.

## Initial scaffold (2026-11-14)

## Implemented

- Python package structure using pybind11 and scikit-build-core.
- Pinned, offline-verifiable generated Kalos source snapshot and license notices.
- Real C++ `convolve` call, core revision/provider metadata and truthful capability reporting.
- Owned input buffers, GIL release and calling-thread signal checks.
- Small standard-library unittest smoke suite.

## Deferred deliberately

Full estimation/preparation bindings, NumPy adapters, public binary wheels,
private bundled OpenBLAS and import-order qualification. Kalos owns the numerical
roadmap; rkalos owns R boundaries. No Python seasonal-adjustment fitting is claimed.

## Local validation completed

The source distribution builds a wheel successfully with scikit-build-core 1.1.2
and pybind11 3.1.0. The installed wheel passes all **3** smoke tests, covering a
real numerical call, input validation/reuse and exact revision/provider metadata.
Snapshot verification checks **84 files**, pinned to Kalos
`4f0625cf44d9cba3c512fdd3d97e1ec4b10132da`. The local CPython 3.15/macOS ARM64
wheel links external OpenBLAS 0.3.34 and the same libomp as that provider.
It contains only the Python module, extension and package/license metadata.
It is a local validation artifact, not a portable public binary-wheel release.

A Linux source-build smoke workflow is configured and pins its core build-tool
checkout. Remote CI, portable wheels and full model APIs are not claimed.

## Linux (x86_64) baseline qualification — 2026-11-15

Qualified on Ubuntu 24.04.4 LTS x86_64, g++ 13.3.0 (Ubuntu 13.3.0-6ubuntu2),
CMake 3.28.3 (system) with ninja 1.13.2, scikit-build-core 1.1.2 and
pybind11 3.1.0 (isolated build env). The effective interpreter was CPython
**3.12.3** (pyenv build, GCC 13.3.0), not 3.11 as originally assumed; a clean
venv with pip 26.3 / build 1.6.1 was used.

`tools/sync-core.py --verify` passed offline: 84 files verified against
`4f0625cf44d9cba3c512fdd3d97e1ec4b10132da`. `pip wheel . --no-deps` produced
`pykalos-0.1.0-cp312-cp312-linux_x86_64.whl`
(sha256 `8a490f316b48ade22bfcf320d441a3128784a87a53cde7509c85f790c75dc1f7`)
with zero compiler warnings. The installed wheel passes all **3** smoke tests
(`python -m unittest discover -s tests -v`: test_core_call, test_metadata,
test_validation_and_reuse). REPL check: `core_version()` reports commit
`4f0625cf…`, provider `OpenBLAS 0.3.34 DYNAMIC_ARCH NO_AFFINITY USE_LOCKING
SkylakeX SINGLE_THREADED`, `blas_integer_bits: 32`, `openmp: True`;
`capabilities()` reports `{'fit': False, 'primitives': ('convolve',),
'status': 'minimal_binding'}`; `convolve([1,-0.4],[1,0.2])` returns
`[1.0, -0.2, -0.08000000000000002]`. `ldd` on the installed extension
resolves `libopenblas.so.0` to the externally built, pinned **0.3.34** LP64
CBLAS/LAPACKE provider (`/tmp/opencode/openblas/lib`), and `libgomp` to the
system library. The wheel does **not** vendor the provider, so it is a local
machine-bound artifact; portable public binary wheels remain undone.

Two Linux-specific defects were found and addressed honestly:

1. The first wheel **failed to import** (`undefined symbol:
   LAPACKE_dpotrf_work`). Ubuntu 24.04's `libopenblas-dev` ships an
   `openblas.pc` that leads the vendored `FindKalosOpenBLAS` pkg-config hint
   ahead of `OpenBLAS_ROOT`, so the extension silently linked the system
   0.3.26 **NO_LAPACKE** library while headers came from the pinned root.
   Qualification therefore pins the finder cache explicitly:
   `-DOpenBLAS_ROOT=… -DKalosOpenBLAS_INCLUDE_DIR=…/include
   -DKalosOpenBLAS_LIBRARY=…/lib/libopenblas.so`. The vendored finder is
   unedited; hardening it (or vendoring the provider via auditwheel) is a
   follow-up task.
2. The extension had no install RPATH, so the loader picked the system
   `libopenblas.so.0` regardless of what was linked. `CMakeLists.txt` now
   sets `INSTALL_RPATH` to `$ORIGIN` plus the resolved OpenBLAS library
   directory on Linux, and the qualified wheel was rebuilt with it.
   Caveat: this machine's `LD_LIBRARY_PATH` exports
   `/usr/lib/x86_64-linux-gnu`, which outranks `DT_RUNPATH`; baseline
   commands above ran with `LD_LIBRARY_PATH` unset. On a default
   environment no override is needed.

## M1: OpenBLAS resolution hardening — 2026-11-15

`vendor/kalos/` was not touched; its `FindKalosOpenBLAS.cmake` snapshot still
resolves pkg-config hints ahead of `OpenBLAS_ROOT`. pykalos now shadows it with
its own hardened finder, `cmake/FindKalosOpenBLAS.cmake` (pykalos-owned),
invoked by the top-level `CMakeLists.txt` via `find_package(KalosOpenBLAS
REQUIRED)` *before* `add_subdirectory(vendor/kalos)`. Because the snapshot's
`find_package` short-circuits on the cached `KalosOpenBLAS_FOUND` and reuses
the parent-scope `Kalos::OpenBLAS` target, the snapshot finder never runs in a
pykalos build. Hardening, versus the snapshot:

1. An explicit `OpenBLAS_ROOT` cache entry (or env var) is **authoritative**:
   headers/library are searched with `NO_DEFAULT_PATH` inside that root only;
   pkg-config (`/usr/.../openblas.pc`) participates only when no root is
   given. A resolved include dir or library outside an authoritative root
   (e.g. an explicit `-DKalosOpenBLAS_LIBRARY=` override) is a `FATAL_ERROR`
   naming both paths.
2. The resolved pair is always probe-linked for `LAPACKE_dpotrf_work`
   (`try_compile` over `cmake/kalos_openblas_probe.cpp`, the exact symbol that
   broke the first baseline wheel); a provider lacking LAPACKE fails configure
   with a `FATAL_ERROR` naming the mismatched header/library pair instead of
   failing later at `import pykalos`.

Verification (all under `env -u LD_LIBRARY_PATH`):

- Positive: bare `cmake` configure with **only** `-DOpenBLAS_ROOT=/tmp/opencode/openblas`
  succeeds; log shows `Found KalosOpenBLAS` plus `KalosOpenBLAS probe OK:
  LAPACKE_dpotrf_work links against /tmp/opencode/openblas/lib/libopenblas.so`.
- Hazard A (header/lib mix via cache override): `-DOpenBLAS_ROOT=/tmp/opencode/openblas
  -DKalosOpenBLAS_LIBRARY=/usr/lib/x86_64-linux-gnu/libopenblas.so` fails at
  configure with "OpenBLAS_ROOT is authoritative … but KalosOpenBLAS_LIBRARY
  points outside it", naming both paths.
- Hazard B (LAPACKE-less provider hidden inside a root): fake root with pinned
  `include/` plus a `lib/libopenblas.so` symlink to the system 0.3.26
  NO_LAPACKE library passes the path check but fails the probe: "OpenBLAS
  provider probe failed: linking LAPACKE_dpotrf_work failed", naming
  `…/include/lapacke.h` and `…/lib/libopenblas.so`. No undefined-symbol
  surprise can reach import time anymore.
- Wheel rebuilt cleanly with `pip wheel . --no-deps` and only
  `--config-settings=cmake.args="-DOpenBLAS_ROOT=/tmp/opencode/openblas"`
  (no `KALOS_*` cache overrides): `pykalos-0.1.0-cp312-cp312-linux_x86_64.whl`,
  sha256 `151b23ad87f44cd9b8d2a2abab559322f387af8b92e639b56ad3143c4d8b2a24`.
  All **3** smoke tests pass against the installed wheel; `ldd` resolves
  `libopenblas.so.0` to the pinned `/tmp/opencode/openblas/lib` and `libgomp`
  to the system library.

### Bundling spike (auditwheel 6.8.2 + patchelf, documented, not shipped)

`auditwheel show`: wheel tag `linux_x86_64`; extension's dependency graph
references versioned symbols of `libgomp` (OMP_1.0/GOMP_4.0) and
`libgfortran.so.5` (GFORTRAN_8) and glibc symbols up to GLIBC_2.38,
constraining it to manylinux_2_38. `auditwheel repair` (needs `patchelf`)
succeeded: it resolved `libopenblas.so.0` through the embedded RPATH to the
pinned 0.3.34 file **at the /tmp path**, copied it plus `libgomp` and
`libgfortran` into a top-level `pykalos.libs/`, renamed them
(`libopenblas-r0-84de4eab.3.34.so`, `libgomp-135f3c8f.so.1.0.0`,
`libgfortran-342618cc.so.5.0.0`), rewrote `NEEDED`/`RPATH`
(`$ORIGIN:$ORIGIN/../pykalos.libs`, dropping the absolute /tmp path) and
retagged to `manylinux_2_38_x86_64` (89 KB → 12.2 MB). Installed into a
pristine venv, that wheel passes all 3 smoke tests with every numeric library
resolving inside the wheel — filename/SONAME collisions with the system
`libopenblas.so.0` are avoided by auditwheel's hash renaming.

Remaining gaps before any public wheel, matching the `dependencies/README.md`
requirement of *private symbols/library names*: auditwheel renaming fixes file
names only, **not** symbol names — the vendored OpenBLAS still exports global
`LAPACKE_*`/BLAS symbols, so coexistence with NumPy's own bundled OpenBLAS in
one process remains an interposition hazard; publishable wheels need a
provider built with namespaced/suffixed symbols (plus single-threaded +
`USE_LOCKING` and a conservative CPU baseline per the README) and both NumPy
import orders validated. manylinux_2_38 is also weak portability: build inside
a manylinux container for a lower glibc baseline and reduce the
`libgfortran`/`libgomp` vendoring surface. No provider binaries are vendored
in this repository.

## M1: core snapshot refresh — 2026-11-15

The requested refresh target, kalos `8e91ee4268eadc434a92f235928f43d6e4edad1d`,
is **provably unbuildable as a snapshot and was not adopted**: upstream's own
`tools/source-files.json` core allowlist (83 entries, unchanged since
`4f0625cf…`) was never extended when `0d20d21` added `src/x11_sigma.cpp` +
`include/kalos/x11_sigma.hpp` and `8e91ee4` added `src/x11_replacement.cpp` +
`include/kalos/x11_replacement.hpp`, yet both commits list the new sources in
`CMakeLists.txt`. `sync-core.py` exports exactly the manifest, so a snapshot at
those pins misses required sources — the wheel build fails at configure with
`CMake Error at vendor/kalos/CMakeLists.txt:34 (add_library): Cannot find
source file: src/x11_replacement.cpp`. Neither the vendor snapshot nor the
lock was hand-patched to fake around it. With the orchestrator's approval the
pin was refreshed instead to the newest self-consistent commit, kalos
**`c6a1881c58968e919e0ed3d82b3f436af25ad47f`**, which carries both requested
platform-independent pieces — the binary64 underflow-guard semantics
(`0cbd012`) and the upstream `FindKalosOpenBLAS` explicit-`OpenBLAS_ROOT`
precedence fix (`c6a1881`) — while the x11_sigma/x11_replacement numerical
units remain excluded until upstream repairs its manifest (their contracts/
fixtures are not part of the python-kind export anyway).

Lock delta `4f0625cf…` → `c6a1881…`: **84 → 84 files, zero additions, zero
removals**; 11 vendor files content-refreshed (9 numerics sources with the
underflow guards, the regenerated `include/kalos/revision.hpp`, and the
updated `cmake/FindKalosOpenBLAS.cmake`). `sync-core.py --verify` passes
offline on the new pin.

Finder compatibility: the refreshed snapshot finder (upstream rewrite) uses
the same cache variables (`KalosOpenBLAS_INCLUDE_DIR`/`_LIBRARY`/`_FOUND`) and
the same `Kalos::OpenBLAS` target as pykalos's shadow module, and its new
explicit-root semantics agree with the shadow's; the shadow still runs first
and the snapshot's `find_package` short-circuits on the cached result, so the
upstream module never executes in a pykalos build (configure log shows exactly
one `Found KalosOpenBLAS` and the shadow's `KalosOpenBLAS probe OK` line). No
adaptation of the shadow module was required; it is kept because it is
strictly stronger (root-containment `FATAL_ERROR`s and the LAPACKE
`try_compile` probe versus upstream's warning-only check).

Qualified on Linux x86_64 with **only** `-DOpenBLAS_ROOT=/tmp/opencode/openblas`
under `env -u LD_LIBRARY_PATH` (no cache-pair overrides anymore): zero-warning
wheel `pykalos-0.1.0-cp312-cp312-linux_x86_64.whl`, sha256
`af6a53ba5323bf706a52f027202b99d0ffa65a5f7868094478fb055a596f80a6`; all **3**
smoke tests pass; installed extension links the pinned external **0.3.34**
provider (`ldd` → `/tmp/opencode/openblas/lib/libopenblas.so.0`, system
`libgomp`); `core_version()` reports commit `c6a1881c…` with unchanged
provider metadata. **No new Python surface was exposed** — the bindings
roadmap (still `core_version`, `capabilities`, `convolve`) is unchanged.

## M1 (final): pin advanced to f96603f — 2026-11-15

Upstream fixed the manifest gap proved above: kalos `f96603fac2f37ef62ebd637b455fed44ca7bad28`
extends `tools/source-files.json` to 87 core entries (adding
`src/x11_sigma.cpp`, `src/x11_replacement.cpp`, `include/kalos/x11_sigma.hpp`,
`include/kalos/x11_replacement.hpp`; the same commit also grows the R-kind
fixtures list to 132 entries) and adds `tools/check-manifest.py`, which fails
upstream CI if a `CMakeLists.txt` source is not in the manifest. That guard is
why advancing is now safe; pykalos's pin moved `c6a1881…` → `f96603f…`.

`sync-core.py --kind python` refreshed the snapshot offline-verifiably:
**84 → 88 vendor files** — exactly the four 22b.3 core files added, **zero
removals** (plus content updates to `vendor/kalos/CMakeLists.txt` and the
regenerated `revision.hpp`); the fixture entries stay out of the python-kind
export as designed. `sync-core.py --verify`: PASS (88 files, `f96603f…`).

Wheel evidence (Linux x86_64, venv, `env -u LD_LIBRARY_PATH`, **only**
`-DOpenBLAS_ROOT=/tmp/opencode/openblas`): the pykalos shadow finder still
runs first and the refreshed snapshot finder short-circuits (one
`Found KalosOpenBLAS` + shadow `probe OK` in the configure log); the new
`x11_sigma`/`x11_replacement` translation units compile into the core library;
zero-warning wheel `pykalos-0.1.0-cp312-cp312-linux_x86_64.whl`, sha256
`a8514c1588fe4259d5378708e5edab3114f22d24bcdc1f4d0eb148ef50edc249`; all **3**
smoke tests pass; `ldd` still resolves `libopenblas.so.0` to the pinned
external 0.3.34 provider; `core_version()['commit']` reports `f96603fac2f37…`.
No new primitives are exposed to Python — `capabilities()['primitives']` is
still `('convolve',)`; the bindings roadmap is unchanged.

## M1 (follow-up): pin advanced to cd004b0 — 2026-11-15

Kalos delivered `cd004b08bcb6cdf1e5b22b2cf34af721ccbaf06c` ("Make profiled
variances binary64 quotients for bit-identical recomputation"), the last
scratch-width divergence of the underflow-guard family, found by the rkalos
re-qualification against the `f96603f` pin: both likelihood kernels produced
the named `profiled_variance` as a once-rounded extended quotient while the
prediction kernels divide the stored binary64 sum in binary64 — 1 ULP apart
on x86-64. The pin moved `f96603f…` → `cd004b0…`; `sync-core.py --kind
python` changed exactly `vendor/kalos/src/diffuse_state_space.cpp`,
`vendor/kalos/src/regression_likelihood.cpp`, the regenerated `revision.hpp`
and `core.lock.json`; `sync-core.py --verify` PASS (88 files).

Wheel rebuilt with **only** `-DOpenBLAS_ROOT=/tmp/opencode/openblas` under
`env -u LD_LIBRARY_PATH`: zero warnings,
`pykalos-0.1.0-cp312-cp312-linux_x86_64.whl`, sha256
`229f1fddd535d8f7e6972c80dded3c4817fe35df6c83ede643a998a927b758c8`; all
**3** smoke tests pass; `core_version()['commit']` = `cd004b08…`; under
`env -u LD_LIBRARY_PATH` the extension resolves `libopenblas.so.0` to the
pinned `/tmp/opencode/openblas/lib` (with the ambient `LD_LIBRARY_PATH` the
system 0.3.26 shadows the SONAME at load, per the known host hygiene note).
No new Python surface exposed; bindings roadmap unchanged.

## M2: NumPy interoperability qualification — 2026-11-16

**Decision (minimal surface): the boundary was kept as-is.** The acceptance
study against the pinned cd004b0 build (pybind11 3.1.0 `std::vector<double>`
type caster) showed the "list-only" assumption wrong: `convolve` *already*
accepts the full required interop set — Python sequences and iterables,
float64 NumPy arrays and views (contiguous, strided, negative-stride),
read-only buffers (`setflags(write=False)`, `memoryview` of `frombuffer`
bytes), `memoryview` and narrower dtypes via per-element conversion. It
rejects 2-D/0-D arrays, `bytes` and `str` with `TypeError`. NaN/Inf/empty
inputs raise the core's own `ValueError` ("polynomial coefficients must be
finite" / "…at least one coefficient") — the binding adds no policy, which is
exactly the promised mirror of core statuses. Masked arrays are rejected:
NumPy converts masked elements to NaN (with its own UserWarning) and the core
refuses non-finite coefficients. Because every accepted path **copies into
owned vectors before the GIL is released**, copy-in stays (zero-copy would let
GIL-holding Python threads mutate caller memory that the lock-free
computation still reads; the copy of 1M doubles costs milliseconds next to
O(n·m) convolution). A custom caster replicating this would add risk without
adding surface. The qualification therefore landed as: the boundary contract
written into the `convolve` docstring (no behavior change), the interop test
suite below, and the import-order study. `capabilities()['primitives']`
remains `('convolve',)`.

**Tests:** new `tests/test_numpy_interop.py` (9 tests, skips cleanly without
numpy): float64 arrays, non-contiguous/negative-stride/row views, read-only
buffers, dtype conversions (int64/float32/bool) and generators/tuples,
non-vector rejection, NaN/Inf/empty core-policy `ValueError`s, masked-array
rejection, copy-in non-aliasing (mutating the input after the call cannot
change results), and 1M-element contiguous + 500k strided timing sanity. Full
suite **12/12 OK** (3 smoke + 9 interop) in 0.17 s.

**Import-order qualification (feeds the public-wheel work).** Environment:
venv numpy 2.5.5 (bundles private-namespaced
`numpy.libs/libscipy_openblas64_-4b78795a.so`), pinned provider
`/tmp/opencode/openblas` (0.3.34), system `libopenblas.so.0` = Ubuntu 0.3.26
NO_LAPACKE present on this host. Under `env -u LD_LIBRARY_PATH`,
numpy-first, pykalos-first and interleaved use all pass; `/proc/self/maps`
shows both BLAS libraries coexisting; NumPy results are bit-identical before
and after loading pykalos — no interposition with PyPI NumPy. Two hazards
were proven, not assumed: (1) an already-loaded *system* `libopenblas.so.0`
(preloaded via `ctypes` with `RTLD_GLOBAL`, as a distro NumPy linking the
system BLAS would do) satisfies pykalos' `NEEDED` by SONAME **before** the
extension's RUNPATH is consulted, and import then fails with `undefined
symbol: LAPACKE_dpotrf_work`; (2) the host's ambient `LD_LIBRARY_PATH`
(system multiarch dir) likewise shadows the pinned SONAME at import. Both
confirm that publishable wheels need the auditwheel-spiked private provider
(namespaced symbols + names), as `dependencies/README.md` requires.

Wheel evidence (rebuilt after the docstring change, only
`-DOpenBLAS_ROOT=/tmp/opencode/openblas`, `env -u LD_LIBRARY_PATH`): zero
warnings, `pykalos-0.1.0-cp312-cp312-linux_x86_64.whl`, sha256
`c5df4a7d41e53fbc2f4a5cb772ed7d6f0c6390e37b92019c7419d3d3b6dac047`; installed
extension resolves `libopenblas.so.0` → `/tmp/opencode/openblas/lib` and
`libgomp` → system; `core_version()['commit']` remains `cd004b08…`.

## M2: pin advanced to 16f2785 — 2026-11-16

Routine pin advance `cd004b08…` → **`16f27859896cc2c2faae69e72e7c24e088f93153`**
("Qualify the complete fixed additive B pass", 22b.4 S1 — the S1-equivalent
upstream work including the B-pass sources, fixtures and manifest completion).
Pre-checked upstream-side before syncing: its `tools/check-manifest.py`-guarded
manifest now carries 89 core entries covering all 40 `CMakeLists.txt` sources.
`sync-core.py --kind python`: **88 → 90 vendor files** — exactly
`src/x11_b_pass.cpp` + `include/kalos/x11_b_pass.hpp` added, **zero removals**
(fixtures stay R-kind), plus content updates to `vendor/kalos/CMakeLists.txt`
and the regenerated `revision.hpp`; `--verify` PASS offline (90 files).

Wheel rebuilt with only `-DOpenBLAS_ROOT=/tmp/opencode/openblas` under
`env -u LD_LIBRARY_PATH`: zero warnings, the new `x11_b_pass.cpp` compiles
into the core, `pykalos-0.1.0-cp312-cp312-linux_x86_64.whl`, sha256
`df77fbfc102f672fa63a154725351fa762326ab9204ff2e1261849cc66d76936`; full
suite **12/12 OK** (3 smoke + 9 NumPy interop); `ldd` unchanged
(`libopenblas.so.0` → pinned `/tmp/opencode/openblas/lib`, system `libgomp`);
`core_version()['commit']` = `16f27859896cc…`. Surface unchanged:
`capabilities()['primitives']` remains `('convolve',)`; the B-pass unit is in
the pinned core but not exposed to Python.

## M2: batched pin advance to 2b93ab0 — 2026-11-16

Batched advance `16f2785…` → **`2b93ab00ab69708b2e5b871f313bed567a04a686`**
(spanning allocation staging, all pseudo-additive/decomposition modes and the
restricted fixed-model `x13_fit` composition + corpus); pykalos's pin is now
**realigned with rkalos at 2b93ab0**. Pre-checked upstream: the manifest
carries 101 core entries covering all 45 `CMakeLists.txt` sources; 243
fixture entries stay R-kind. `sync-core.py --kind python`: **90 → 102 vendor
files, zero removals** — 12 additions including the expected
`include/kalos/x11_decomposition.hpp`, `src/x13_allocation.cpp`/`.hpp` and
`src/x13_fit.cpp`/`.hpp` plus the intervening `x11_c_pass`, `x11_d_pass`,
`x11_selection_pass` and `detail/x11_pinned.hpp` units; `x11_b_pass.*`,
`CMakeLists.txt` and `revision.hpp` content-updated. `--verify` PASS offline
(102 files).

Wheel (bare `-DOpenBLAS_ROOT=/tmp/opencode/openblas`, `env -u
LD_LIBRARY_PATH`): zero warnings, all five new core translation units
compile, `pykalos-0.1.0-cp312-cp312-linux_x86_64.whl`, sha256
`9e287af9cb895f3e98f44c204b13dd72b4fa4da65a7baa2b5e5bd7754751a052`; full
suite **12/12 OK** (smoke + NumPy interop); linkage unchanged (pinned
0.3.34 provider + system `libgomp`); `core_version()['commit']` =
`2b93ab00ab697…`. **Surface unchanged**: `capabilities()['primitives']` is
still `('convolve',)` — `x13_fit` exists in the pinned core but is **not**
exposed to Python, per the bindings roadmap.

## M2: pin advanced to e490169, lock schema 2 — 2026-11-17

Pin `2b93ab0…` → **`e490169c95d287c1e66d0b930bf30ddc10a777e8`** (21-A
estimator units: pinned estimation control + Hannan–Rissanen initializer).
Upstream `tools/source-files.json` is now **three-sectioned** (`core: 105`,
`fixtures: 112`, `evidence: 139` after the evidence-root restructure).
pykalos's `tools/sync-core.py` was updated to match: exports still take the
`core` section only for the python kind, and new locks are written as
**schema 2** with per-snapshot **section provenance** (`"sections": ["core"]`
for `vendor/kalos`); `--verify` accepts schema 1 (existing pins) and 2 and
enforces provenance on new locks. Pre/post verification: schema-1 lock
verified before the export (old and new tool agree), schema-2 lock verified
after — `106 files` (`105` core + generated `revision.hpp`), **zero
fixture/evidence leakage** into `vendor/kalos` (checked by path prefix).

Lock delta `2b93ab0…` → `e490169…`: **102 → 106 vendor files, zero
removals** — added `src/estimation_control.cpp`, `include/kalos/estimation_control.hpp`,
`src/hannan_rissanen.cpp`, `include/kalos/hannan_rissanen.hpp`; ten
content-updated files (CMakeLists, backend/lapack/linear-algebra headers,
`x13_allocation.hpp`, `x13_fit.hpp`, `x11_replacement.cpp`, `x11_sigma.cpp`,
`revision.hpp`).

Wheel (bare `-DOpenBLAS_ROOT=/tmp/opencode/openblas`, `env -u
LD_LIBRARY_PATH`): zero warnings, both new estimator translation units
compile, `pykalos-0.1.0-cp312-cp312-linux_x86_64.whl`, sha256
`9d671e48e136e8af332fbedb878db3e00ccd67860fe660393c9b417a8c90c5e2`; suite
**12/12 OK**; linkage unchanged (pinned 0.3.34 provider, system `libgomp`);
`core_version()['commit']` = `e490169c95d28…`. **Surface unchanged**:
`('convolve',)` — the 21-A estimator units are present in the pinned core but
not exposed.

## M2: pin advanced to e19df2c — 2026-11-17

Pin `e490169…` → **`e19df2c7b7ded8fa90424a2945d48a2c43e676b9`** (21-B
log/level transformation decision + 21-C outlier scoring/forward selection,
plus three pinned-semantics fixes isolated in new R-unbound/C-unbound units
with an append-only `estimation_control` warm-start entry). All kalos reads
went through git objects at that commit (`git show/archive`), never its
working tree, which another agent was editing concurrently. Upstream manifest:
111 core entries covering all 50 `CMakeLists.txt` sources (guard-clean);
fixtures 112 / evidence 150 stay R-kind.

Delta inventory `e490169…` → `e19df2c…`: **106 → 112 vendor files, zero
removals** — added `src/transformation_decision.cpp` + `.hpp`,
`src/outlier_scoring.cpp` + `.hpp`, `src/outlier_scan_engine.cpp`,
`src/outlier_detail.hpp`; content-updated: `estimation_control.{cpp,hpp}`
(append-only), `CMakeLists.txt`, regenerated `revision.hpp`. Schema-2 lock
with provenance `sections: ["core"]`; **zero fixture/evidence leakage**
(path-prefix scan: none). `--verify` PASS pre (106 @ e490169) and post
(112 @ e19df2c).

Wheel (bare `-DOpenBLAS_ROOT=/tmp/opencode/openblas`, `env -u
LD_LIBRARY_PATH`): zero warnings, all three new translation units compile,
`pykalos-0.1.0-cp312-cp312-linux_x86_64.whl`, sha256
`17295ddd08cd1b41df3042f309f1fb9e161397b0b48396844c6e244e761f030f`; suite
**12/12 OK**; linkage unchanged (pinned external 0.3.34 provider, system
`libgomp`); `core_version()['commit']` = full `e19df2c…` hash.
**No surface change**: `capabilities()['primitives']` remains `('convolve',)`
— the 21-B/21-C units are pinned in the core but deliberately unbound,
mirroring rkalos: R/Python-boundary qualification of intermediate estimator
units lands with the 21-G/H spec-level slices.

## M2: pin advanced to 2170435 — 2026-11-18

Pin `e19df2c…` → **`21704352cfc8c6af45e68041e42a9e7eb6d4f44d`** (item 21-D:
differencing decision + support cluster). Kalos was mid-next-slice in its
working tree; all upstream reads went through git objects at that commit
only. Manifest pre-check (git show): core **122** entries covering all 55
`CMakeLists.txt` sources; fixtures 112 / evidence 154 remain R-kind.

Delta inventory `e19df2c…` → `2170435…`: **112 → 123 vendor files, zero
removals** — added `src/differencing_decision.cpp` + `.hpp`,
`src/fdlibm.cpp` + `detail/fdlibm.hpp`, `src/ssq_levmar.cpp` +
`detail/ssq_levmar.hpp`, `src/ssq_deviances.cpp` + `detail/ssq_deviances.hpp`,
`src/sarima_stabilization.cpp` + `detail/sarima_stabilization.hpp`, and
`detail/hannan_rissanen_pipeline.hpp`; content-updated: `CMakeLists.txt`,
`estimation_control.{cpp,hpp}` (EstimationSolver seam), `hannan_rissanen.cpp`
(HR refactor with the four transcription fixes — a core **behavior change but
non-surface**: HR is not bound to Python, and the pinned smoke/interop suite
is unaffected), regenerated `revision.hpp`. Schema-2 lock, provenance
`["core"]`, **zero fixture/evidence leakage**. `--verify` PASS pre (112 @
e19df2c) and post (123 @ 2170435).

Wheel (bare `-DOpenBLAS_ROOT=/tmp/opencode/openblas`, `env -u
LD_LIBRARY_PATH`): zero warnings, all five new translation units compile,
`pykalos-0.1.0-cp312-cp312-linux_x86_64.whl`, sha256
`f7bbeee6cd24c42c5a5b7cead17d327ef43cfb0777d533a779bd7947192d7b6e`; suite
**12/12 OK**; linkage unchanged (pinned external 0.3.34 provider, system
`libgomp`); `core_version()['commit']` = full `2170435…` hash.
**No surface change**: `capabilities()['primitives']` remains `('convolve',)`
— the 21-D units are pinned in the core but deliberately unbound until the
spec-level slices, mirroring the rkalos decision.

## M2: pin advanced to 0930c9b — 2026-11-18

Pin `2170435…` → **`0930c9b153928735b80a0f4150373216544aeca7`**, advancing
**directly past the intermediate `7200a56`** so one pin covers both item 21-E
(initial ARMA identification) and item 21-F (ARMA refinement/comparison).
Kalos reads exclusively via git objects at `0930c9b` (working tree
mid-next-slice elsewhere). Manifest: core **126** covering all 57
`CMakeLists.txt` sources; fixtures 112 / evidence 170 R-kind only.

Delta inventory `2170435…` → `0930c9b…`: **123 → 127 vendor files, zero
removals** — added `src/initial_arma_identification.cpp` + `.hpp` and
`src/arma_refinement.cpp` + `.hpp`; content-updated: `CMakeLists.txt`,
`include/kalos/differencing_decision.hpp` and regenerated `revision.hpp`.
Correction to the handoff brief: the 21-D deterministic record-initialization
fix landed in **`differencing_decision.hpp`** (verified `2170435..0930c9b`
diff: header 21+/15−; the `.cpp` is unchanged), and the HR transcription fixes
are now four slices back. Schema-2 lock, provenance `["core"]`, **zero
fixture/evidence leakage**; `--verify` PASS pre (123) and post (127).
Both behavior changes are **non-surface**: none of the 21-E/21-F/21-D units
is bound to Python; `capabilities()['primitives']` remains `('convolve',)`
(21-E/21-F pinned but deliberately unbound, mirroring rkalos until the
spec-level boundary slices).

Wheel (bare `-DOpenBLAS_ROOT=/tmp/opencode/openblas`, `env -u
LD_LIBRARY_PATH`): sha256
`e97c67065ad98def55577a791b297eb333f79dad3c0a57c90ce911716eea366b`; both new
translation units compile; suite **12/12 OK**; linkage unchanged (pinned
external 0.3.34 provider + system `libgomp`); `core_version()['commit']` =
full `0930c9b…`.

**Upstream warning flagged (not pykalos-fixable, vendor is read-only):** the
wheel build emitted **22 `-Wc++20-extensions` warnings**, all from
`vendor/kalos/src/initial_arma_identification.cpp` (lines 516–524), which
uses C++20 designated initializers in a target that declares
`cxx_std_17`; g++ 13 accepts them as GNU extensions but MSVC/`-pedantic-errors`
would reject them. Zero warnings originate from pykalos-owned code.
Recommendation: upstream should either bump the core to `cxx_std_20` or
rewrite those initializers positionally; rkalos compiles the same snapshot
and will see the same noise.

## M2: pin advanced to e7af23f — 2026-11-19

Pin `0930c9b…` → **`e7af23f222315e320ab30338ff8188e74bd444ed`** (item 21-G
regression stage tests + mean rules). Kalos read exclusively via git objects
at that commit. Manifest: core **128** covering all 58 `CMakeLists.txt`
sources; fixtures 112 / evidence 179 R-kind only. Delta: **127 → 129 vendor
files, zero removals** — added `src/regression_variable_tests.cpp` +
`include/kalos/regression_variable_tests.hpp`; content-updated
`CMakeLists.txt` and `revision.hpp`. Schema-2 lock, provenance `["core"]`,
zero fixture/evidence leakage; `--verify` PASS pre (127) and post (129).

Wheel (bare `-DOpenBLAS_ROOT=/tmp/opencode/openblas`, `env -u
LD_LIBRARY_PATH`): sha256
`e920471adf080d5e5354b40d79fb28f9164235c60b008a053a5cde543d1f02d8`; the new
translation unit compiles; suite **12/12 OK**; linkage unchanged (pinned
external 0.3.34 provider + system `libgomp`); `core_version()['commit']` =
full `e7af23f…`. The warning count is unchanged at the **22 known vendor
`-Wc++20-extensions` occurrences** from `initial_arma_identification.cpp`
(flagged upstream in the previous entry; no new warnings). **Surface
unchanged**: `capabilities()['primitives']` = `('convolve',)` — the 21-G unit
is pinned in the core but unbound like all other estimator units, mirroring
rkalos.

## Ops: scratch root relocated — 2026-11-19

The maintainer moved the scratch root: **`/tmp/opencode` is dead** (its
symlink was intentionally deleted; a stray leftover directory exists there
but holds no live provider/venv). All scratch now lives at
**`/data/home/kowa/seasonaladjustment/tmp_opencode`** ("SCRATCH") — pinned
provider `SCRATCH/openblas` (LP64 CBLAS/LAPACKE 0.3.34, unchanged build),
venv `SCRATCH/venv-pykalos` (recreated; CPython 3.12.3; its `bin/*` script
shebangs of moved origin are broken — invoke tools as
`SCRATCH/venv-pykalos/bin/python -m pip/...`). Environment note for
successors: build with
`CMAKE_ARGS=-DOpenBLAS_ROOT=/data/home/kowa/seasonaladjustment/tmp_opencode/openblas`
(still bare, shadow finder authoritative) under `env -u LD_LIBRARY_PATH`.

Operational repair performed (no pin change, still `e7af23f222315…`): the
previously installed wheel's embedded RUNPATH pointed at the dead
`/tmp/opencode/openblas/lib`, so import failed with the system SONAME
fallback (`undefined symbol: LAPACKE_dpotrf_work`). Rebuilt the wheel from
HEAD against the SCRATCH provider:
`pykalos-0.1.0-cp312-cp312-linux_x86_64.whl`, sha256
`59328b286673b93e3e6a0e5e9d696fa028f109d5deb87ff315c607a3f905e08d`
(22 warnings, all the known vendor `-Wc++20-extensions` occurrences, none
new); reinstalled into SCRATCH/venv-pykalos; **12/12 suite OK**; `ldd`
resolves `libopenblas.so.0 =>
/data/home/kowa/seasonaladjustment/tmp_opencode/openblas/lib/libopenblas.so.0`
(+ system `libgomp`); `core_version()['commit']` unchanged,
`primitives` still `('convolve',)`. A repo scan for embedded `/tmp/opencode`
paths found only the historical dated entries above (deliberately unedited);
the pykalos-owned build tooling needed no change — README documents
`/path/to/openblas` generically and the CI workflow uses `runner.temp`.

## M2: pin advanced to b773d27 — 2026-11-20

Pin `e7af23f…` → **`b773d27a66ef2ee50445a6930c307111efc99ff8`** (the 21-H
slice: stage-Z decision-unit qualification, 21-H.0 final-information
producer, 21-H.1 automatic-pipeline driver, 21-H.2 JVM-oracle
qualification, plus `3a54b95` replacing the C++20 designated initializers
and `b773d27` pinning unfused FP semantics). Kalos reads exclusively via
git objects at that commit (its working tree held untracked scratch files;
tracked files equal the commit). Manifest pre-check: upstream
`check-manifest.py` PASS at b773d27 — core **140** entries covering all
add_library sources; fixtures 112 / evidence 190 stay R-kind.

Delta inventory `e7af23f…` → `b773d27…`: **129 → 141 vendor files, zero
removals** — added `src/x13_automatic.cpp` + `.hpp`,
`src/final_estimator.cpp` + `include/kalos/final_estimator.hpp`,
`src/final_information.cpp` + `.hpp`, `src/arma_diagnostics.cpp` + `.hpp`,
`src/special_functions.cpp` + `include/kalos/detail/special_functions.hpp`,
`include/kalos/detail/filter_utility.hpp`, `src/mlj_engine.hpp`;
content-updated: `CMakeLists.txt` (adds the PUBLIC
`-ffp-contract=off` block), `fdlibm.cpp`, `initial_arma_identification.cpp`
(initializer cleanup), `outlier_scan_engine.cpp` (bulk extraction into the new `mlj_engine.hpp`),
`ssq_levmar.cpp`, regenerated `revision.hpp`. Schema-2 lock, provenance
`["core"]`, zero fixture/evidence leakage; `--verify` PASS pre (129 @
e7af23f) and post (141 @ b773d27). The provider lock
(`dependencies/openblas.lock.json`) is unchanged, so the SCRATCH OpenBLAS
0.3.34 build was reused as-is — the pin machinery exports sources only.

**FP-semantics pin verified end-to-end.** b773d27 adds
`target_compile_options(kalos PUBLIC -ffp-contract=off)` (GNU/Clang;
`/fp:precise` on MSVC). In the pykalos build it propagates via the
INTERFACE of the `kalos::kalos` target consumed through
`add_subdirectory(vendor/kalos)` + `target_link_libraries(_kalos …)`;
verified `CMAKE_EXPORT_COMPILE_COMMANDS=ON` + a verbose clean rebuild:
**all 65 translation units** — 64 vendor core objects **and the pykalos
binding TU `bindings/module.cpp`** — carry `-ffp-contract=off` on their
g++ command lines (e.g. `… -O3 -DNDEBUG -fPIC -fvisibility=hidden
-flto=auto -fno-fat-lto-objects -ffp-contract=off -fopenmp …
bindings/module.cpp`). This is what the 21-H.2 JVM goldens require
(unfused `a*b+c`).

Wheel (`SCRATCH/venv-pykalos`, `env -u LD_LIBRARY_PATH`, bare
`-DOpenBLAS_ROOT=/data/home/kowa/seasonaladjustment/tmp_opencode/openblas`):
**zero compiler warnings anywhere** — the 22 known vendor
`-Wc++20-extensions` occurrences from `initial_arma_identification.cpp`
(flagged since the 0930c9b entry) are gone via upstream `3a54b95`;
`pykalos-0.1.0-cp312-cp312-linux_x86_64.whl`, sha256
`a23593186cb71470717999c877e9672d76b39f01289d90b64f8991641994f5b6`;
installed RUNPATH `$ORIGIN:…/tmp_opencode/openblas/lib` preserved and
`ldd` (with `LD_LIBRARY_PATH` unset) resolves `libopenblas.so.0` →
SCRATCH 0.3.34 provider + system `libgomp`.

Suite: **12/12 OK** under `pytest` 9.2.0 (first pytest run — installed
into the venv; the same 12 tests as the previous `unittest discover`
checkpoints) with `LD_LIBRARY_PATH=SCRATCH/openblas/lib`;
`core_version()['commit']` = full `b773d27…`.

**Drift verdict: bit-identical.** A 7-case convolve corpus captured from
the installed e7af23f wheel (smoke, unit, Henderson-symmetric, asymmetric
linspace, 4096×257 seeded-RNG, subnormal 1e-300/3e-308, 1e150 large-scale)
was re-run after reinstall: every output's sha256-over-binary64-bit-patterns
matches exactly; `capabilities()` unchanged
(`('convolve',)` — the entire 21-H automatic-pipeline surface is pinned in
the core but deliberately unbound, mirroring rkalos). Only
`core_version()['commit']` differs, as expected. This matches upstream's
own local validation: the plain x86-64 baseline has no FMA to contract,
so the flag changes nothing on this host — it pins the semantics for FMA
machines (arm64, x86-64-v3 CI images) where the 21-H.2 goldens would
otherwise drift.

## M4: automatic preprocessing bound at the Python boundary — 2026-11-20

Pin `b773d27…` → **`b2573fc011aee37eced0e97ddfd86d88349887c2`** (item 21-H.3:
the oracle closed at thirteen cases — airline-start ODM fix, JVM-surface
AR/SAR export signs, landing-AICC adjusted log-likelihood, golden-generator
factory-index ODM translation; upstream gates at that commit: oracle
4637/0, sweep 71401/0, ctest 62/62 serial+OpenMP). Upstream
`check-manifest.py` PASS first (140 core / 112 fixture / 190 evidence).
Delta `b773d27…` → `b2573fc…`: **141 → 141 vendor core files, zero
additions/removals** — content-only updates to `CMakeLists.txt`,
`include/kalos/outlier_scoring.hpp`, `src/outlier_scoring.cpp`,
`src/x13_automatic.cpp` + regenerated `revision.hpp`; schema-2 lock, `--verify`
PASS pre (141 @ b773d27) and post (141 core + 6 evidence @ b2573fc).

**Machine extension — the evidence snapshot.** The boundary tests replay the
JVM-pinned corpus, and pykalos had no fixture convention (the convolve tests
carry their data inline), so the pin machinery grew the one auditable
mechanism the schema was designed for: for `--kind python`, the upstream
`evidence` section is now exported for a minimal directory allowlist
(`EVIDENCE_ALLOWLIST = validation/evidence/native/x13-automatic/` only) into
a **separate `vendor/kalos-evidence` snapshot with provenance `["evidence"]`**
(6 files: cases/inputs/oracle-events/oracle-facts CSVs + metadata.R +
SHA256SUMS.csv, 775 KB). Nothing leaks into `vendor/kalos` (the core snapshot
stays `["core"]`-only and the `--verify` exactness now covers both
directories); sdist packaging extended accordingly.

**The automatic capability.** `_kalos.x13_automatic_fit(request: dict) ->
dict` binds the core entry verbatim: the raw layer REQUIRES every decoder
scalar (missing key → KeyError; unknown enum name → ValueError) including the
REQUIRED sigma policy (unset → the pinned
`unsupported:x13 fit requires an explicit sigma policy`); the request dict is
fully read into owned C++ before the GIL is released, the whole result graph
(final description, coefficients, variables, landing stats, the complete
pinned decision chain with each machine's projected record — scalars/notes
kept verbatim as ordered pair lists — and the downstream composition with
the three qualified tables) converts back to plain dicts. Shape violations
map the core's `std::invalid_argument` onto ValueError. The product entry
`pykalos.x13_automatic(series, *, frequency, start_year, start_period, mode,
sigma, …, **module-scalar overrides)` applies the FAMILY decisions at this
layer only: omitted `sigma` → the maintainer 2026-11-17 default `"legacy"`,
echoed as `result["sigma_policy_provenance"]` = `"legacy (default)"` /
`"legacy (explicit)"` / `"accurate (explicit)"`; the decoder-pinned module
scalars (`_X13_AUTOMATIC_DEFAULTS`, JVM-corpus values incl. the module-space
`ub1 = 1/1.0309278350515465` reciprocal doubles) and the decoder X-11 block
(msr seasonal, automatic Henderson, `"undefined"` mode) default here and stay
explicit toward the core. `capabilities()["primitives"]` is now
`('convolve', 'x13_automatic')` plus an `automatic` block (schema 2,
`sigma_policy_default: "legacy"`, envelope, deferred list).

**Fail-closed matrix (verified in the suite, no silent fallback to the
restricted fit — no restricted surface exists here):** Python `ValueError`/
`TypeError` before the core call for unknown mode/policy/msr/seasonal/
outlier-type names and any unexpected keyword (regression inputs have NO
surface; the error says user-variable detection is deferred to 21-I); the
core's verbatim statuses otherwise — non-monthly,
non-finite input, `backcast/forecast != 0`, deferred
calendar/easter/TD/user flags, outlier span narrower than the series
(0-based endpoints), and the raw-entry missing policy; all keep
`available=False` with the provenance echo.

**Qualification.** `tests/test_x13_automatic.py` + `tests/x13auto_corpus.py`
(the corpus reader mirrors the core's golden generator: `req`-echo request
mirror with module-space reciprocal conversion, event kinds 1–5, `var`-fact
identities, three tables; `test_evidence_sha256sums` hashes the vendored
files against `SHA256SUMS.csv`). The full thirteen-case oracle ran in the
foreground: **32 passed + 7 subtests, 6m53s; 4353 checks, 0 failures; all
13 cases decision-bit-identical** — every case status `available`; final
descriptions, `mode_effective`, neff, variable identities (name/type/
position/regeffect), differencing triples, ARMA selections, panel
membership, ODM picks and incoming cv bits, cascade remarks, chain counts:
all exact (model-facts 92/92, variables 45/45, diff-decisions 39/39,
arma-decisions 52/52, odm-decisions 20/20, chain-counts 52/52). Measured
worsts vs the contract bands — **no relaxation**: tmean 7.423e-4 (1e-3,
multi/diff0), panel BIC2 8.095e-3 (1e-2, ao_nodet — upstream's 8.1e-3),
AICC display 3.418e-6 (1e-5), landing loglik/aicc/regcoef 4.482e-7 (2e-3),
ARMA landing coefficients 9.747e-3 (1e-2, ao_nodet — upstream's 9.8e-3),
tables 5.036e-7 (1e-6, multi/out[48] — upstream's 5.0e-7); the eight
outlier-free cases' tables are bit-identical, the pinned deterministic-chain
behaviour. Default `pytest tests` set = the 12 baseline tests + the corpus/
boundary tests + the eight outlier-free cases: **27 passed** (the cheap tier
upstream itself designates); detection-on cases run via
`PYKALOS_X13AUTO_CASES`.

Wheel (`env -u LD_LIBRARY_PATH`, bare
`-DOpenBLAS_ROOT=SCRATCH/openblas`):
`pykalos-0.1.0-cp312-cp312-linux_x86_64.whl`, sha256
`3a1ff4a4f637ccdd28ebfc318f3e80f50fca438685d08a4dfa52387dec150af3`, **zero
compiler warnings**, RUNPATH `$ORIGIN:SCRATCH/openblas/lib` intact (ldd with
the ambient `LD_LIBRARY_PATH` unset resolves the pinned 0.3.34 provider +
system `libgomp`), `core_version()['commit']` = full `b2573fc…`. Clean-tree
`compile_commands.json` re-verified: **65/65 translation units carry
`-ffp-contract=off`** (64 vendor + the binding TU `bindings/module.cpp`) —
the PUBLIC propagation of the vendored CMakeLists survives the binding
growth. **Drift verdict: none at the Python boundary** — decisions
bit-identical to the JVM pins across the suite's two full 13-case
executions; the sigma-default trio (`legacy (default)`/`legacy (explicit)`/
`accurate (explicit)`) answers identically on quick, the convolve surface
unchanged (baseline 12/12 green on the final wheel).

## M5: pin advanced to f500162 — horizon envelope extended and qualified — 2026-11-21

Pin `b2573fc…` → **`f500162a3be1539803566f9bc8f071e0deb4f66b`** (item 21-H.4:
the `arima_forecasts` unit plus the nonzero-horizon `initialStep` route wired
into the automatic driver, incl. the estimation-block AR sign fix; the
intervening `7564ce7` is workflow-only). Upstream `check-manifest.py` PASS at
f500162 first (142 core / 112 fixture / 195 evidence). Vendor delta:
**141 → 143 core files** — added `include/kalos/arima_forecasts.hpp` +
`src/arima_forecasts.cpp`; content-updated `CMakeLists.txt`,
`x13_allocation.hpp/.cpp`, `x13_automatic.hpp/.cpp` + regenerated
`revision.hpp`.

**Machine extension — evidence allowlist (maintainer decision, recorded).**
The checkpoint STOP of 2026-11-20 escalated the discovery that 21-H.4
deliberately deletes the core's zero-horizon refusal; the recorded decision is
to advance the pin AND extend the horizon envelope, qualified against the
upstream JVM horizon captures. `EVIDENCE_ALLOWLIST` in `tools/sync-core.py`
grew from `x13-automatic/` only to also include
`validation/evidence/native/x13-horizon/`: the vendored `vendor/kalos-evidence`
mirror is now **11 files** (the six 21-H oracle files plus the five horizon
captures — cases/inputs/oracle-facts CSVs + metadata.R + SHA256SUMS.csv, R
4.5.1/JVM 21 double-captured on 2026-11-20, provenance `["evidence"]`, own
SHA256SUMS gate). Nothing leaks into `vendor/kalos` (still `["core"]`-only).
`--verify` PASS pre (141 core + 6 evidence @ b2573fc) and post
(143 core + 11 evidence @ f500162).

**The envelope change — horizons {0..N}, otherwise unchanged.** At b2573fc
`src/x13_automatic.cpp` refused nonzero X-11 horizons
(`unsupported:x13 fit requires zero horizons`); the driver at f500162 delivers
the route instead: horizons are month counts (negative = |h| annual
frequencies, normalized by the driver, echoed normalized in `fit`) and feed
the downstream composition ONLY — estimation, the decision chain and the
landing coefficients are horizon-invariant
(x13-automatic-pipeline-contract.md, "Horizon extension (21-H.4)"). EVERY
OTHER fail-closed pin stays verbatim: non-monthly, non-finite input, deferred
calendar/easter/TD/user flags (21-I), outlier span < series, raw-entry missing
sigma policy, unknown spec names, regression inputs. capabilities()
`automatic` block bumps to **schema 3**: `zero_horizon_only` replaced by
`horizon_envelope`; the raw-entry docstring and the wrapper docstring now say
horizons `{0..N}`.

**Re-pin and qualification.** The fail-closed matrix entries `backcast=1` and
`forecast=2` are re-pinned to the new contract (accepted: `status available`,
`available=True`, `fit` horizon echo, `out` length `n+bc+fc`). New
`tests/test_x13_automatic_horizon.py` (+ `load_horizon_corpus()` in the corpus
reader) replays the four JVM horizon captures through
`pykalos.x13_automatic`. NO relaxation: at the boundary the exposed decisions
are BIT (status, final description, `mode_effective`, variable identities,
neff, horizon echo, table lengths) and numerics ride the upstream bands
transcribed from `tests/jvm_x13_automatic_horizon.h` kCases at f500162 for the
three boundary-exposed tables (`HZ_BANDS`, copied never widened; the bit-tier
`a1`/`d18`/`d18a`/`d18b` claims live upstream — those tables do not cross the
binding); landing coefficients and stats reuse the existing zero-horizon
contract bands (1e-2/2e-3) because the horizon captures pin byte-identical
landing facts. Case selection `PYKALOS_X13HZ_CASES`, default the
detection-free `quick_h6`; `test_evidence_sha256sums` now verifies both
captures.

Wheel (`SCRATCH/venv-pykalos`, `env -u LD_LIBRARY_PATH`, bare
`-DOpenBLAS_ROOT=SCRATCH/openblas`):
`pykalos-0.1.0-cp312-cp312-linux_x86_64.whl`, sha256
`97ae136e9585bf3b477c4cf9989e5f9b1f9c46d83b1b995fc2a326c6128857b4`, **zero
compiler warnings**, **66/66 TUs carry `-ffp-contract=off`** (65 vendor — the
64 + `arima_forecasts.cpp` — plus the binding TU), RUNPATH
`$ORIGIN:SCRATCH/openblas/lib` intact (ldd with the ambient `LD_LIBRARY_PATH`
unset resolves the pinned 0.3.34 provider + system `libgomp`),
`core_version()['commit']` = full `f500162…`.

Suites. Default `pytest tests`: **30 passed + 7 subtests** (27 + the two
horizon shape tests + the `quick_h6` qualification; the re-pinned pair keeps
the matrix 7/7 green). Full gate (both detection sets, `-s`, 11m09s):
**38 passed + 7 subtests, 0 failures**. Zero-horizon oracle scoreboard
**4353 checks / 0 failures — every measured worst byte-identical to the M4
record** (tmean 7.423e-4, panel BIC2 8.095e-3, AICC display 3.418e-6, landing
stats 4.482e-7, landing coefficients 9.747e-3, tables 5.036e-7). New horizon
scoreboard **1287 checks / 0 failures**: all bit families exact
(decisions/echo/lengths/variables/status), worsts well inside the transcribed
bands — out 1.047e-6 (band 2e-5, so_h6), d11final 3.130e-7 (5e-6, so_h6),
e11 3.763e-7 (5e-6, multi_b3h6), hz landing coefficients 3.003e-4 (1e-2),
landing stats 3.507e-8 (2e-3). **Drift verdict: beyond the recorded contract
change, none** — the zero-horizon surface is bit-stable and the horizon
acceptance is JVM-qualified at the core's own tiers. CI note: the
`smoke.yml` core-tools checkout ref `4f0625c` needs no move —
`tools/build-openblas.py` is the identical blob (`69285ff…`) at f500162.

## REVIEW-1: request-validation hardening at the Python and raw-bindings boundary — 2026-11-23

Adopts the two P1 sections of `adaption_in_the_implemetation_needed.md`
(external review dated 2026-11-23 at `808e01c`, tracked at the repo root,
referenced never edited): **"Validate the Python automatic-fit request
before coercion"** and **"Reject unknown raw keys and negative budgets"**.
Core pin unchanged (`f500162…`); no `vendor/` file touched; the raw
entry's explicit-sigma contract and the convenience entry's legacy
default are verbatim unchanged (pinned by
`test_explicit_sigma_contract_unchanged`).

**Python boundary (`src/pykalos/__init__.py`).** New private validators
(`_request_int/_request_flag/_request_float/_request_span/_request_series`)
run before any use of a request value; the function body contains no
`int()`/`bool()`/`float()` coercion left. Documented policy table lives on
the `x13_automatic` docstring (pointer from the module docstring),
mirrored in C++ comments. Decisions: integer slots accept `int` and
`__index__` integer scalars (numpy integers) — the review's RECOMMENDED
strict set — and refuse `bool` and EVERY float including an integral one;
flags accept `bool` and `numpy.bool_` only (duck-typed, no numpy import;
the type-name check covers numpy 1 `bool_` and numpy 2 `bool` spellings);
`outlier_span` takes exactly two integer endpoints; the series refuses
`str`/`bytes`/bytearray/memoryview, mappings, sets, 0-D/>1-D arrays and
text/non-scalar elements, keeps ordered iterables, 1-D arrays and numeric
scalars, and leaves NaN/Inf elements to the core's documented
"complete finite series" status (M2 convolve doctrine). The per-month
seasonal default is allocated only from the validated frequency.
Well-formed-but-unsupported requests are NOT pre-empted: `frequency=4`
still reaches the core and keeps `unsupported:x13 automatic fit monthly
series only`; deliberately NO range rules were added at the boundary
(negative `backcast`/`forecast` are legal 21-H.4 semantics; any range
check would pre-empt core statuses).

**Raw boundary (`bindings/module.cpp`).** `validate_request_keys` checks
every dict key against the 44-required/6-optional raw schema and raises
`TypeError` naming all unknown keys — the `use_calender_detection` typo
can no longer silently vanish (the review's observation that the same
status came back is pinned fixed). Both budgets are sign-checked BEFORE
the `size_t` conversion (negative → `ValueError` naming field and value;
the old `-1 → SIZE_MAX` wraparound is pinned fixed). Every field is read
through explicit typed getters (`req_int/req_bool/req_double/req_str/
req_series` + manual `outlier_types`/span parsing): integers must
implement `__index__` (`bool` refused; note EVERY ndarray satisfies
`PyIndex_Check` because numpy fills the slot, so the conversion itself is
the scalar test in `req_series`), flags must be real Python `bool`s (the
raw entry refuses `numpy.bool_` — documented asymmetry versus the product
entry), text/binary containers and per-element text are refused, and all
failure messages name the field and the offending type (replacing
pybind11's anonymous `Unable to cast … type '?'` `RuntimeError`s with
`TypeError`s). One deliberate widening: a **generator** `input` now
reaches the core (the old vector caster rejected it with the anonymous
RuntimeError while the wrapper's `float()` path had always accepted
generators; the raw entry now matches the documented iterable policy).

**Coercion before/after (probe list; `tmp_opencode/review1/pre-probe*.log`
BEFORE on the pre-change wheel — extracted from `dist/` — and
`post/final-probe*.log` AFTER on the final wheel).**

| input (entry) | BEFORE | AFTER |
|---|---|---|
| `frequency=12.9` (wrapper) | sent `frequency=12` | `TypeError: … 'frequency must be an integer, got the float 12.9; fractional values are refused (no truncation) …'` |
| `start_period=1.9` (wrapper) | sent `first_period=1` | `TypeError` naming `start_period` |
| `forecast=0.9` (wrapper) | sent `forecast=0` (horizon silently removed) | `TypeError` naming `forecast` |
| `backcast=float('nan')` (wrapper) | `ValueError` from `int()` | `TypeError` (consistent class) |
| `frequency='12'` / `frequency=True` (wrapper) | sent 12 / sent **1** (`["msr"]*1` allocated) | `TypeError` both |
| `start_year=1970.5`, `trend_length=0.9` (wrapper) | sent 1970 / 0 | `TypeError` both |
| `outlier_span=(0,5,9)` (wrapper) | sent `(0, 5)` (third dropped) | `TypeError: … needs exactly two integer endpoints, got 3 values …` |
| `outlier_span=(0.9,5.9)` (wrapper) | sent `(0, 5)` | `TypeError` naming `outlier_span[0]` |
| `outlier_span='12'` (wrapper) | sent `(1, 2)` (string indexing!) | `TypeError` (text refused) |
| `use_calendar_detection='False'`, `outliers='False'` (wrapper) | sent **True** | `TypeError: … 'False' would have meant True` |
| `use_user_variables=1` (wrapper) | coerced True by truthiness | `TypeError` |
| digit-string / bytes series (wrapper) | reached the core as `[1.0,2.0,…]` | `TypeError` (text/binary refused) |
| multivariate list / 2-D ndarray / np scalar / **dict** / `['1.5',…]` series (wrapper) | confusing `TypeError` / **dict iterated its keys silently** / strings float()-parsed | clear `TypeError`s, all refused |
| `frequency=np.int64(12)`, `np.bool_` flags, np-int span, int64/float64 1-D arrays (wrapper) | accepted | **still accepted** (pinned) |
| unknown key `use_calender_detection` (raw) | **silently ignored, same status** | `TypeError: … unknown key(s): use_calender_detection …` |
| `outlier_max_round=-1` / `outlier_max_outliers=-2` (raw) | status `available` (SIZE_MAX budget) | `ValueError: … must be non-negative, got -1` |
| budgets negative via `**overrides` (wrapper) | same wraparound | same `ValueError` (raw parser, pinned) |
| flag `'False'`/`1`/`np.True_` (raw) | str → anonymous `RuntimeError`; **int/np.True_ coerced to True** | `TypeError` naming field, all three |
| digit-string/bytes/memoryview `input` (raw) | anonymous `RuntimeError` | `TypeError` naming `'input'` |
| `input=['101.0',…]` (raw) | `RuntimeError` (whole list rejected) | `TypeError` ("text elements are refused") |
| 2-D ndarray `input` (raw) | anonymous `RuntimeError` | `TypeError` ("non-scalar element of type ndarray") |
| `sigma=b'legacy'` (raw) | **accepted** (string caster took bytes) | `TypeError` |
| `frequency=12.9`/`True`, `backcast=0.9`, `outlier_span=(0.9,5.9)`/3-tuple (raw) | anonymous `RuntimeError` | `TypeError`s naming fields |
| input generator (raw) | `RuntimeError` (rejected) | **accepted** (documented widening) |
| valid monthly request (both entries), quarterly `frequency=4`, NaN series, narrow span, deferred flags | core statuses | **identical** core statuses (pinned rows) |

**Tests.** New `tests/test_request_validation.py`: **52 tests + 51
subtests** — every malformed probe-list input through the entry that
accepted it (wrapper slots/flags/span/series; raw keys/budgets/flags/
input/span incl. the mapping/set raw-input regression), the
typo/negative/valid trio through **both** entries, accepted-interop pins
(numpy int scalars, `np.bool_` on the product entry only), and status
rows pinning the existing core responses unchanged: monthly valid
`available`, quarterly valid `…monthly series only`, deferred-flag,
NaN-series finite, narrow-span refusal, missing `mode` `KeyError`
message, explicit-sigma contract.

**Gates (all under `env -u LD_LIBRARY_PATH`, provider
`SCRATCH/openblas`, wheel `pykalos-0.1.0-cp312-cp312-linux_x86_64.whl`
sha256 `5d08fdd5f03d84a583e1f2d9e0650a3e29f520fcb0b6b494c4c60da7da1876e8`,
zero compiler warnings, `ldd` → pinned 0.3.34 + system `libgomp`).**
Default `pytest tests`: **30 passed + 7 subtests → 82 passed + 58
subtests** (30 + the 52 new), 0 failures, 3m01s; smoke stays 3/3,
discovery baseline 30 confirmed (`unittest discover` runs the new file
identically to pytest). **Bit-unchanged verdict: proven** — the M4 and
horizon scoreboard blocks (worst relative deviations per family, `-s`
capture `pre-default-suite.log` vs `final-default-suite.log`) are
**byte-identical pre/post** apart from the pytest summary line: landing
coefficients keep worst `9.747e-03` at `ao_nodet/arma1` (the four
review-named landing cases live in the default tier), landing stats
`4.482e-07` at `ao_nodet/aicc`, tables `5.385e-16` at
`mode_logadd/e11[64]`, hz quick tier `1.845e-07` at `quick_h6/out[101]`
— identical in both captures. The detection tier was re-verified on the
final wheel separately: `ao,ls,multi,so` → 11 passed + 7 subtests, 1375
checks 0 failures (tmean `7.423e-04` multi/diff0, tables `5.036e-07`
multi/out[48]); horizon `ao_b3,multi_b3h6,so_h6` → 5 passed, 974 checks
0 failures (out `1.047e-06` so_h6, d11final `3.130e-07`, e11
`3.763e-07`) — every worst reproduces the M4/M5 records verbatim.

**Review-check diagnostic ("four landing-coefficient failures on
macOS/Homebrew — repeat with the qualification provider BEFORE changing
tolerances").** On Linux x86-64 with the **qualified OpenBLAS 0.3.34
provider** the four cases (`ao_nodet`, `mode_logadd`, `mode_mult`,
`mode_pseudo`) **PASS both before and after this change** — they live in
the default (outlier-free/forced-mode) tier, so the pre/post default
suite replays above already carry them (byte-identical landing
coefficient worst `9.747e-03` at `ao_nodet/arma1`); a dedicated
four-case run added the isolated evidence: pre-change wheel 11 passed +
7 subtests, 1324 checks 0 failures (167.75s), post-change wheel 11
passed + 7 subtests, same 1324 checks 0 failures, worsts reproducing the
M4 record (landing coefficients `9.747e-03` at `ao_nodet/arma1`, panel
BIC2 `8.095e-03` at `ao_nodet/arma0/panel2/bic`, tmean `4.841e-04` at
`ao_nodet/diff0/tmean`). No tolerance was touched and none is needed on
this provider; the divergence is a property of the reviewer's Homebrew
provider build, not of the pinned-qualification path.

**Adjudication (where the review over-states or under-states).**
(1) The `'False' → True` flag coercion is a WRAPPER behavior only — the
raw entry already refused strings, albeit with an anonymous
`RuntimeError` (`flag='False'` BEFORE rows above); the fix still had to
land in both places because the raw entry accepted `1`/`np.True_` as
True. (2) "digit string and bytes reached the core as series input" is
confirmed via the wrapper's `float()` path and a raw request dict
carrying them; the raw container cast itself rejected them. (3) "check
scalar integer fields for exact values **and range**" was implemented as
exactness+type only: boundary range rules would pre-empt documented core
statuses (monthly-only, negative-horizon envelope) — recorded deviation,
tests pin the core statuses instead. (4) Undocumented siblings found and
fixed while at it: dict series iterated keys silently; `frequency=True`
became 1 and `["msr"]*1` allocated from it; `sigma=b'legacy'` accepted
raw. (5) Reviewer's `__init__.py#L119`/`module.cpp#L63/#L473/#L424` line
refs verified against the pre-change tree (drift < 10 lines).

**Deferred (dated, deliberate — nothing silently dropped).**
All remain gated on the **next core pin advance**, per slice
instruction "both ride the pin advance":
- P2 "solver and horizon metadata agree with the pinned core"
  (`capabilities()["automatic"]["estimation_solver"] = "bfgs_default"`
  vs the pinned header's `PinnedLevenbergMarquardt`; `horizon_envelope`
  wording vs negative = annual-frequency semantics; capability-test
  extension): the alignment must quote the NEW core's contract, so it
  lands with the pin advance, not against the old header.
- P2 "Exercise NumPy and make provider qualification reproducible"
  (dedicated NumPy CI lane in `smoke.yml`, provider
  version/config/fingerprint logging from the wheel test env,
  `smoke.yml` core-tools tooling-pin `4f0625c` bump): the workflow's
  provider-tooling ref and the capability-dict edits belong to the same
  pin-advance batch so CI and the lock move atomically.
- NumPy test lane stays skip-clean today (numpy IS installed in the
  qualification venv; the 9 interop tests + this slice's numpy cases
  ran here, not skipped).
Datable hygiene: no dated external data involved — nothing to pin.


### M5 fitted-model and ordinary RSA0 checkpoint

The export advances to core `fa7edeae3c68862e163633c7debce3d102248223`, which includes typed WK component rows, the fitted TRAMO deterministic-effects merge, and the ordinary monthly TR0 estimator and RSA0 product pipeline. The SEATS extraction and bridge evidence now ship alongside the preceding Python corpora, including the direct raw-series RSA0 oracle. Offline verification covered all 194 core files and 46 evidence files. Python binding and installed-wheel qualification for these contracts follow this integration commit.

### M5 fixed-model WK extraction and fitted TRAMO decomposition

Python now exposes `seats_extract_wk` for fixed monthly models and `seats_from_tramo` for fitted likelihoods and deterministic AO/LS effects. Both return owned, dated rows and preserve the core’s status and refusal reasons. The installed wheel replayed all 36 WK cases (1,055 rows, 55,812 values). The fitted bridge replayed all six requests, including four successful merges (8,160 values) and both approximation refusals. Dates, ordering, lengths and binary64 values, including signed zeros, matched the frozen oracles. [Installed-wheel replay](tests/test_seats.py)

### M5 ordinary monthly RSA0 product fit

`tramoseats_fit` estimates the TR0 mean and airline coefficients directly from original monthly observations, then returns the RSA0 WK and merged components and the four observed final series. Capability metadata specifies the RSA0 template, complete monthly input, additive mode and the approximation boundary. Broader TRAMO templates and approximation retries remain outside this fit. [API](README.md) · [Raw series replay](tests/test_tramoseats_fit.py)

All six original-series JVM fits agreed bit-for-bit on the two MA coefficients, mean coefficient, log likelihood, residual sum of squares, 60 merged component rows and 3,960 values. The installed macOS ARM64 wheel also passed alternate calendar, horizon and request refusal checks. All 76 WK, RSA0, fixed X-13, preprocessing, smoke, NumPy, import-order and input validation tests passed at one thread with pinned OpenBLAS 0.3.34.

### M6 private OpenBLAS wheels and repair gates

The opt-in POSIX wheel build links the checksum-pinned single-threaded LP64 archive into the module. The linker hides the archive symbols. The installed module reports the provider linkage, version, integer ABI and runtime configuration. The bundled-wheel gate rejects exported BLAS/LAPACKE/configuration symbols and any dynamic OpenBLAS dependency. Hosted jobs build inside manylinux_2_28 x86-64 and on macOS, repair the Fortran/OpenMP dependencies, verify a clean install, and run both NumPy import orders. [Workflow](.github/workflows/portable.yml) · [Provider check](tools/check-wheel-provider.py)

On macOS ARM64 a repaired 2.98 MB wheel passed all 76 targeted tests, including the WK/bridge/RSA0 corpora and both NumPy import orders. Its sole exported symbol was the Python initializer. The repaired dependency list contained the system C/C++ runtime and wheel-private GCC, Fortran, quadmath and OpenMP libraries. The private extension’s SHA-256 was `d168133737bb1ae58aab5f872a464ffc63b090baf14c4d2024d613856d53ae8e`. The local compiler runtime requires macOS 27.2 even though wheel tags encode 27.0; the hosted macOS job enforces the minimum deployment target represented by its wheel tag. Hosted deployment-target and manylinux qualification are pending. No package release was made.

### M5 RSA0 forecast uncertainty checkpoint

The core pin advances to `2fe3d8e8c8b6bfeae9fa4224517e9e0c12228fe8`. It supplies independent original-series forecast errors from the fitted preprocessing model and the existing WK forecast uncertainty. Offline verification covers 194 core and 47 evidence files. The binding gate checks six forecast domains against 144 original-series standard errors at the core’s covariance threshold and 144 WK values bit-for-bit, plus signed and zero horizons.

### M5 Python forecast uncertainty on the original series

`tramoseats_fit` now returns the preprocessing model’s `series_forecast_stdev`, its own status and the dated forecast domain. The WK Series/StdevForecast row remains available for component uncertainty. Python normalizes the signed horizon once for both projections. The repaired private-provider wheel passed all 77 targeted tests. For all six fits, 144 original-series standard errors passed the frozen covariance budget (2e−8 × (1 + |reference|)); all 144 paired WK standard errors were bit-exact. Alternate and zero horizons passed. [Prediction tests](tests/test_tramoseats_fit.py)

### Python real-valued input qualification

NumPy complex scalars previously reached real-valued series, parameter and convolution slots through scalar conversion, which discarded their imaginary parts. The product and raw automatic-fit boundaries now reject complex scalars explicitly, and convolution checks each coefficient while copying it into the owned vector. The regression reproduced the loss on the preceding wheel. All 78 targeted tests passed on the repaired private wheel with NumPy, including the complex64, complex128 and extended-precision cases, strided/memoryview inputs and large-array timing checks. [Boundary tests](tests/test_numpy_interop.py)

### M6 Windows wheel qualification job

The Windows lane builds the same private LP64 archive under UCRT64, links against the native CPython ABI, gathers compiler-runtime notices and repairs dependent DLLs with delvewheel. A separate PowerShell step installs the wheel outside the build shell, checks the PE import table, replays the component fixtures and exercises both NumPy import orders. The macOS private build and checker still pass. Local PE parsing accepted a control executable and rejected an OpenBLAS DLL import. The Windows runner must complete the actual build, clean install and tests before Windows portability can be claimed. [Windows job](.github/workflows/portable.yml)

The clean source-archive wheel at Python `eb15c8f` and core `fa7edea` passed the full 102-test suite in 761.5 seconds on macOS ARM64. Its 13 automatic X-13 and four horizon oracle cases made 4,353 and 1,287 checks respectively with zero failures, alongside the restricted X-13, TRAMO preprocessing, WK, bridge, RSA0 and import-order tests.

### M6 hosted provider build reuse

The source-wheel and portable-wheel workflows now reuse a provider build keyed by the core’s OpenBLAS archive lock, build script, runner OS, architecture, profile and toolchain. The manylinux profile uses the exact container image digest for both provider and wheel. UCRT64 keys its installed toolchain packages; native builds key their compilers and runner image. A successful provider build is cached before the independent wheel tests, and each installed wheel still runs its provider and numerical checks. The workflow YAML and Bash/MSYS scripts parsed locally and the native toolchain fingerprint executed on macOS. [Provider action](.github/actions/openblas/action.yml)

The import-order regression also overlaps two concurrent RSA0 workers with two NumPy linear-solve workers. Each import order checks all six seasonal adjustments against the frozen binary64 oracle and twelve NumPy solves against their known solutions. The external provider passed at a Kalos thread limit of two. The private-provider wheel passed at limits one, two and eight with OpenBLAS limited to one thread.

### M6 installed Python wheel and JDemetra+ RSA0 timings

On an eight-core Apple M2 running macOS 27.0.1, native ARM64 CPython 3.15.2 and Temurin 21.0.11+10 ran the same two ordinary monthly fits with one Kalos/OpenMP/OpenBLAS thread and one JVM active processor. The private wheel used core `2fe3d8e`, Clang 23.1.5 and OpenBLAS 0.3.34 built with GNU Fortran 16.2.0. The six JD+ 3.9.0 jars were checked against the frozen bridge reference. Each engine started four fresh processes, with engine order alternating between rounds. Each process warmed each workload with 20 fits, then measured seven batches of five fits. Startup, file loading, JAR checks and oracle comparisons were outside the timings.

| Ordinary RSA0 workload | Observations | Python median ms (interquartile range) | JDemetra+ median ms (interquartile range) | Python / JVM |
|---|---:|---:|---:|---:|
| Airline (`fit_tr0_air`) | 144 | 45.422 (44.230–48.675) | 4.039 (3.732–4.379) | 11.25× |
| Multiple-outlier input (`fit_multi`) | 96 | 34.473 (33.416–36.202) | 6.237 (5.624–6.633) | 5.53× |

Both public routes materialized all 50 initial, final and merged rows, with 3,912 and 2,808 values respectively. They also returned the observed seasonal adjustment and 24 original-series forecast standard errors. All 240 observed adjustments matched the oracle bit-for-bit in both engines. The largest Python forecast-error differences were 2.42e−13 and 1.25e−14. The native ARM64 JVM matched the captured x86-64 public errors exactly on these two cases. Both timed RSA0 fits use the airline SARIMA structure. The older mixed-factor estimation benchmark uses a free ordinary AR, fixed ordinary MA and free seasonal MA; that core performance gate remains open alongside the observed RSA0 latency gap. [Raw samples and build identity](tools/benchmark/results/2026-11-23-macos-arm64.json) · [Benchmark driver](tools/benchmark/rsa0.py)

To repeat, install the wheel for this checkout and run `python tools/benchmark/rsa0.py --jdk <native-Java-21.0.11-home> --jar-dir <toolkit-and-sa-jars> --jar-dir <tramoseats-jars>`. The driver reports all sample times in milliseconds per fit and checks the returned values before emitting the report.

### M5 RSA0 residual checkpoint

The binding snapshot advances from `2fe3d8e` to `5c95dc1`, including the raw TR0 residual projection and its six JVM captures. The integration gate verifies the export, then compares all public residual dates, lengths, values and standard errors at the installed wheel. The prior private-provider snapshot passed all 104 tests, including 5,640 X-13 automatic and horizon checks, in 379.2 seconds. Hosted macOS also passed the private wheel repair, deployment target, numerical and NumPy checks at `cc1e239`. [Hosted macOS job](https://github.com/statistikat/pykalos/actions/runs/45272946518/job/138037208162)

### M5 dated RSA0 preprocessing residuals

`tramoseats_fit` returns the dated preprocessing residuals (`residuals.tsres`) and their public standard error (`residuals.ser`) in its residuals dictionary, and advertises the projection in the restricted RSA0 capability. The repaired installed wheel matched all six residual start dates, all 570 residuals and all six standard errors bit-for-bit. All 78 targeted tests passed, including the forecast-error, full component, NumPy import-order and concurrent-fit regressions. Offline verification covered 194 core and 48 evidence files. [Oracle replay](tests/test_tramoseats_fit.py)

### Java-free installed-wheel numerical gate

A fresh process now starts with an empty executable search directory, missing JDK/JRE homes and an empty classpath. It rejects process creation during the fits and checks the process image list for a JVM before and after running the fixed X-13 corpus, the automatic X-13 quick case and all six original-series RSA0 oracles. The installed private-provider wheel passed on macOS ARM64 without NumPy. The portable Linux, macOS and Windows jobs run the same test before installing NumPy. [Java-free wheel test](tests/test_java_free.py)

### M6 RSA0 forecast covariance performance checkpoint

The source snapshot advances to `9e3afba`, which computes the RSA0 forecast covariance from the fitted monthly model using the specialized projection. The wheel gate repeats the 144 preprocessing and 144 WK uncertainty comparisons, raw fits, import-order and Java-free checks, then repeats the same warmed Python/JVM benchmark on the original two series. The portable workflow still verifies the private provider and checks the installed wheel.

### M2 Python preparation of dated regressors and transformed series

The Python binding now composes the frozen window, regressor alignment and mean/drift preparation units. It returns the extended and observed column vectors, source and observation offsets, ordered coefficient names and fixed/free states. The response preparation entry exposes native transformations and masked log-Jacobian contributions. Shared request checks cover both entries and the existing product fits. On an installed wheel, all 60 preparation, TRAMO boundary, X-13 request validation and Java-free tests passed. The preparation cases covered both frequencies, all eight nonzero regular/seasonal differencing combinations, a window crossing year zero, out-of-window missing values, fixed coefficients, masked Jacobian rows and named refusals. [Tests](tests/test_preparation.py)

### M2 fixed-order estimation evidence checkpoint

The Python export at core `9e3afba` now includes both fixed-order estimation-control corpora. The binding gate replays the frozen Zero, Default, Hannan–Rissanen and Multiple cases with the core's applicable decision, likelihood and parameter budgets, plus fixed-coordinate and rejection checks. The solver and starting policy remain explicit client inputs.

### M6 repeated installed-wheel and JVM timings after the RSA0 covariance change

The `9e3afba` wheel passed all 79 targeted tests, including the complete raw-RSA0, WK, bridge, residual and forecast-error corpora and the Java-free subprocess. The matched Apple M2 benchmark repeated the same four-process warmup, batch size, JVM flags, toolchains and 24-month forecasts. The observed adjustment vectors again agreed bit-for-bit, with identical 50-row payloads. The largest original-series standard-error difference on the timed cases was 7.11e−14.

| Ordinary RSA0 workload | Python median ms (interquartile range) | JDemetra+ median ms (interquartile range) | Python / JVM | Earlier Python median ms |
|---|---:|---:|---:|---:|
| Airline | 2.880 (2.681–3.145) | 5.638 (4.906–6.250) | 0.511× | 45.422 |
| Multiple-outlier input | 3.672 (3.471–3.868) | 8.227 (6.903–9.909) | 0.446× | 34.473 |

The specialized covariance reduced the measured Python medians by factors of 15.8 and 9.4 respectively. On this host both Python medians were below the contemporary JVM medians. Each JVM measurement was repeated; the earlier medians of 4.039 and 6.237 ms document run-to-run variation. [Raw samples](tools/benchmark/results/2026-11-23-macos-arm64-specialized.json)

### M2 explicit fixed-order SARIMA estimation

The installed Python wheel exposes the frozen four starting policies, fixed and free coefficient masks, dated prepared regression designs, both qualified solvers and chronological initialization/optimization/unit-root decisions. It passed all 27 JVM control cases at the core's existing bounds (24 estimated models and three likelihood-only guards), the fully free pinned LM reference, the fixed-coordinate BFGS check and the corresponding solver refusal. All 84 targeted tests passed, including Java-free and NumPy coexistence. Portable wheel CI runs the preparation and estimation checks on each platform. [Estimator tests](tests/test_estimation.py)

### M5 qualified monthly SEATS approximation and residual independence checkpoint

The binding snapshot advances to core `c5bcf97`. The exported source includes the two monthly fitted-model retry policies, their terminal failure handling and the public RSA0 residual independence test. Offline verification covered 194 core files and 57 evidence files. The binding gates replay the fixed-model WK and fitted-model bridge captures, the ordinary RSA0 diagnostic and the short-residual threshold.

### M5 monthly Legacy approximation at the Python boundary

The installed fixed-model WK operation now reproduces the classical airline retry and the degenerate model's JVM matrix-error status. Across the 36 captured WK requests it matched all 1,095 component rows and 58,020 values bit-for-bit, preserving the four named refusal cases. All six fitted-TRAMO bridge fixtures passed, including both mixed AO/LS horizons, with 11,343 values bit-for-bit across the final and merged rows. All 21 targeted wheel tests passed, including NumPy coexistence, Java-free execution and raw RSA0. [Installed-wheel oracle replay](tests/test_seats.py)

### M5 public RSA0 residual independence

The ordinary monthly fit now returns `residuals["lb"]` with the public statistic, upper-tail probability, 22 reference degrees of freedom and 24 lags. The installed wheel matched all six full-series JVM statistics and probabilities bit-for-bit. AirPassengers prefixes of 36, 37 and 38 observations returned the expected undefined, undefined and finite tests, respectively. All 22 targeted wheel tests passed, including fixed-model WK, fitted-model and raw RSA0 components, Java-free imports and NumPy coexistence. [Diagnostic replay](tests/test_tramoseats_fit.py)

### M2 Python signal delivery and module reuse

An installed-wheel subprocess now interrupts a long convolution and a separate fixed-order estimation from a Python timer thread. Both operations delivered `KeyboardInterrupt` to the calling thread, joined the timer and then completed another native operation successfully. The two-process check passed locally in 0.75 seconds. The portable and NumPy jobs run it on their installed wheels. [Signal tests](tests/test_interrupt.py)

### M6 historical monthly fixed-order estimator timings

The prepared Python estimator and both pinned JVM frontend calls were compared on the original monthly airline and mixed-factor cases. Each model covers level/log responses with complete observations or five gaps. Both estimate drift and an external regressor, with a second regressor fixed at 0.2. The mixed model has a free regular AR, fixed regular MA of 0.2, free seasonal MA and one seasonal difference. The original R 4.5.2 oracle manifest verifies the JDemetra+ 3.9.0 packages, JAR hashes and Eclipse Adoptium 27.0.1.0.2 on ARM64.

| Prepared fit | Python ms | JD+ RG0 ms | JD+ TR0 ms |
|---|---:|---:|---:|
| Monthly airline | 3,489.2 | 18.1 | 17.0 |
| Monthly mixed factors | 1,623.7 | 16.8 | 17.0 |

Each number is the arithmetic mean of four case medians after three warmup rounds and five timed batches of three fits per case. Both frontends received prebuilt requests. Python returned its fit record, while each R/JVM frontend returned its public preprocessing result. The shared Apple M2 was running other builds and tests. The raw samples record that variability. All 16 method/case comparisons passed the original coefficient, adjusted likelihood and Jacobian budgets, with maximum absolute differences of 4.96e−7, 1.17e−11 and zero, respectively. Fixed coordinates remained exact. [Reproduction script](tools/benchmark/fixed_order.py) and [samples, versions and thread settings](tools/benchmark/results/2026-11-23-macos-arm64-fixed-order.json)

The generic fixed-order estimator still needs performance work. In a separate direct-C++ probe of the level airline input, one evaluation of `sarima_innovations` with saved gains took 20.8 ms on complete data and 25.0 ms with gaps. The full physical objective measured 21.6 and 25.0 ms respectively, and the optimizer recorded 86 and 85 evaluations. The monthly RSA0 forecast-covariance optimization addresses a separate call path.

### M6 full installed-wheel regression matrix

The bundled Linux, macOS and Windows jobs run the Java-free checks before installing NumPy, then discover the complete wheel suite with all 13 automatic X-13 and four horizon cases. The shared corpus selector accepts `all` and retains the quick default and explicit case lists. Local discovery selected every expected case and the workflow parsed with both full-corpus settings. The earlier initial bundled jobs at `cc1e239` passed on [manylinux](https://github.com/statistikat/pykalos/actions/runs/45272946518/job/138037208627) and [macOS](https://github.com/statistikat/pykalos/actions/runs/45272946518/job/138037208162). The expanded hosted replay and Windows results remain pending.

### M5 monthly calendar F-test checkpoint

The Python snapshot advances to core `854703c`, including the monthly working-day and trading-day candidate fits with explicit significance and numerical precision. Offline verification covered 196 core files and 59 evidence files. The binding gate compares every candidate fit and exact threshold decision across the four dated monthly input series.

### M5 monthly working-day and trading-day selection

`tramo_calendar_f_test` fits both calendar candidate models to dated complete monthly observations with explicit mean, significance and numerical precision. Across the four JVM input regimes and 14 comparisons, all candidate sums of squares, mean squares and lower-tail probabilities matched bit-for-bit. The degrees of freedom, three possible selections and strict/inclusive threshold decisions matched exactly. Negative tests covered calendar domains, input types, residual count and invalid numerical controls. All 88 targeted installed-wheel tests passed. [Calendar qualification](tests/test_tramo_calendar.py)

### Full numerical replay after monthly SEATS retry integration

The repaired macOS ARM64 wheel at core `c5bcf97` passed the complete 111-test discovery run with NumPy. All 4,353 automatic X-13 checks and all 1,287 extended-horizon checks passed. The 849.1-second run also covered the 27 fixed-order estimation controls, fitted and ordinary TRAMO/SEATS, public residual independence, wheel-provider coexistence and Java-free adjustment.

### M5 normality and stock TRfull calendar checkpoint

Core `2bf7cc3` adds the public RSA0 residual normality test and the stock initial TRfull calendar module on monthly original observations. The qualification gates compare the diagnostic structure and binary64 values on the nine RSA0 fits and the calendar decisions, t statistics and candidate fits on the 20 stock level/log cases. The wheel retains its restricted raw-series fit templates until the corresponding final component fixtures pass.

### M5 public RSA0 residual normality

The installed wheel exposes `residuals["doornikhansen"]` and advertises it on the RSA0 template. It reproduced the six full-series and three short-series public JVM statistics and probabilities bit-for-bit, with two degrees of freedom. Seven fitted residuals returned an absent test. All 23 related installed-wheel tests passed. [Residual diagnostics replay](tests/test_tramoseats_fit.py)

### M5 stock TRfull initial calendar decisions

`tramo_full_initial_calendar` accepts dated original monthly observations and the level/log decision. It exposes the stock TRfull working-day/trading-day comparison and the rule's mean, leap-year and Easter t statistics, retention flags and module-change decision. All 20 level/log JVM fits agreed bit-for-bit on the captured numerical outputs and exactly on the optional leap-year test and all decisions. All 86 targeted installed-wheel tests passed. [Stock calendar replay](tests/test_tramo_calendar.py)

### M6 Windows checkout of the locked source and evidence

A fresh checkout with `core.autocrlf=true` modified the locked source and fixture bytes and failed offline verification on this host. Git now preserves the committed bytes under both vendor trees. A second fresh CRLF-configured checkout verified every hash for all 196 core files and 63 evidence files at `2bf7cc3`. Both portable jobs verify this immediately after checkout and before building the provider.

### M5 raw TR1 and M6 finite state prediction checkpoint

Core `5350e96` contains the public fixed-airline TR1 preprocessor from original observations and the optimized finite state predictor. The Python integration checks the six public TR1 preprocessing records, reruns fixed-order oracle agreement, and repeats the original eight-case fixed-order timing matrix with the same JVM, wheel toolchain and thread settings.

### M5 raw monthly TR1 preprocessing

`estimate_tramo_tr1` fits the stock TR1 preprocessing specification from dated complete observations and returns its transformation, model, registered outliers, likelihood and dated full residuals. The repaired wheel matched reference dates, orders, zero-based outlier positions, parameter and regression coefficients, likelihood fields and all 570 residuals across the six public JVM fits. All 92 targeted installed-wheel tests passed, including the 27 fixed-order controls, stock calendar decisions, residual diagnostics and existing adjustment routes. [TR1 replay](tests/test_tramo_automatic.py)

### M6 installed-wheel fixed-order timing after sparse prediction

At core `5350e96`, the eight historical monthly cases returned exactly the same coefficient, adjusted likelihood and Jacobian differences against all 16 JVM method/case references as before. The independent repeat used the same checked R and JVM pins, wheels' compiler and provider profile, processor, single-thread settings, warmups and batches.

| Prepared fit | Previous Python ms | Current Python ms | Current JD+ RG0 ms | Current JD+ TR0 ms |
|---|---:|---:|---:|---:|
| Monthly airline | 3,489.2 | 1,226.1 | 16.1 | 14.3 |
| Monthly mixed factors | 1,623.7 | 552.7 | 18.3 | 16.2 |

The installed Python elapsed-time medians improved 2.85× and 2.94× on the shared host. The separate interleaved direct-C++ experiment measured 2.20× and 2.27× lower CPU time for the same fits. The remaining elapsed-time ratios range from 30.1× to 85.5× across the two JVM frontends and model families. [Repeated samples and numerical agreement](tools/benchmark/results/2026-11-23-macos-arm64-fixed-order-sparse.json)
