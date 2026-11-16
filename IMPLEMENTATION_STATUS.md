# pykalos implementation status

Updated: 2026-11-14. Minimal initial binding, as requested.

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
