# pykalos-hardened OpenBLAS provider finder.
#
# This file is owned by pykalos and deliberately shadows the generated
# snapshot at vendor/kalos/cmake/FindKalosOpenBLAS.cmake (never edit that
# copy; it is re-synced from upstream). The top-level CMakeLists.txt calls
# find_package(KalosOpenBLAS REQUIRED) with this directory prepended to
# CMAKE_MODULE_PATH before add_subdirectory(vendor/kalos), so the snapshot's
# find_package short-circuits on the cached KalosOpenBLAS_FOUND and the
# Kalos::OpenBLAS imported target created here.
#
# Hardening versus the upstream snapshot:
#
#   1. An explicit OpenBLAS_ROOT cache entry (or environment variable) is
#      authoritative: the include directory and library are searched for
#      inside that root only. pkg-config hints (e.g. Ubuntu's openblas.pc,
#      which leads the snapshot's search and silently selects the system
#      NO_LAPACKE 0.3.26 build) are consulted only when no root is given.
#   2. When a root is authoritative, a resolved include directory or library
#      outside that root (explicit cache override or stray cache entry) is a
#      loud configure-time error naming both, never a silent mix.
#   3. The resolved library is always probe-linked against the resolved
#      headers for the LAPACKE_dpotrf_work symbol
#      (cmake/kalos_openblas_probe.cpp). A provider that lacks LAPACKE, or a
#      header/library mismatch, fails at configure time with a FATAL_ERROR
#      naming the mismatched pair instead of an undefined-symbol surprise at
#      Python import.
#
# Explicit -DKalosOpenBLAS_INCLUDE_DIR=... / -DKalosOpenBLAS_LIBRARY=... cache
# entries are still honoured (find_path/find_library do not overwrite set
# cache variables), but they must live inside an authoritative OpenBLAS_ROOT
# and they still face the link probe.

set(_kalos_openblas_root "")
if(OpenBLAS_ROOT)
  file(TO_CMAKE_PATH "${OpenBLAS_ROOT}" _kalos_openblas_root)
elseif(DEFINED ENV{OpenBLAS_ROOT} AND NOT "$ENV{OpenBLAS_ROOT}" STREQUAL "")
  file(TO_CMAKE_PATH "$ENV{OpenBLAS_ROOT}" _kalos_openblas_root)
endif()

if(_kalos_openblas_root)
  # Authoritative root: no pkg-config, no default system search paths.
  find_path(KalosOpenBLAS_INCLUDE_DIR lapacke.h
    HINTS "${_kalos_openblas_root}"
    PATH_SUFFIXES include include/openblas openblas
    NO_DEFAULT_PATH)
  find_library(KalosOpenBLAS_LIBRARY NAMES openblas
    HINTS "${_kalos_openblas_root}"
    PATH_SUFFIXES lib lib64 lib64/openblas lib/openblas
    NO_DEFAULT_PATH)
else()
  # No root requested: behave like the upstream snapshot (pkg-config plus
  # system paths). The LAPACKE probe below still guards against mixes.
  find_package(PkgConfig QUIET)
  if(PkgConfig_FOUND)
    pkg_check_modules(PC_OPENBLAS QUIET openblas)
  endif()
  find_path(KalosOpenBLAS_INCLUDE_DIR lapacke.h
    HINTS ${PC_OPENBLAS_INCLUDE_DIRS}
    PATH_SUFFIXES include include/openblas openblas)
  find_library(KalosOpenBLAS_LIBRARY NAMES openblas
    HINTS ${PC_OPENBLAS_LIBRARY_DIRS}
    PATH_SUFFIXES lib lib64)
endif()

if(_kalos_openblas_root AND (NOT KalosOpenBLAS_INCLUDE_DIR OR NOT KalosOpenBLAS_LIBRARY))
  message(FATAL_ERROR
    "OpenBLAS_ROOT is authoritative for this build but no usable provider was "
    "found inside it:\n"
    "  OpenBLAS_ROOT:              ${_kalos_openblas_root}\n"
    "  KalosOpenBLAS_INCLUDE_DIR:  ${KalosOpenBLAS_INCLUDE_DIR}\n"
    "  KalosOpenBLAS_LIBRARY:      ${KalosOpenBLAS_LIBRARY}\n"
    "Expected lapacke.h under ${_kalos_openblas_root} (include*/...) and a "
    "libopenblas with CBLAS/LAPACKE under lib*/. Unset OpenBLAS_ROOT to fall "
    "back to pkg-config/system discovery (a LAPACKE probe still applies).")
endif()

if(_kalos_openblas_root)
  # Both resolved: they must live under the authoritative root. Anything else
  # means a stale or deliberately overriding cache entry mixing a system
  # library with pinned headers - refuse it instead of guessing.
  foreach(_kalos_resolved IN ITEMS KalosOpenBLAS_INCLUDE_DIR KalosOpenBLAS_LIBRARY)
    file(TO_CMAKE_PATH "${${_kalos_resolved}}" _kalos_resolved_path)
    string(FIND "${_kalos_resolved_path}" "${_kalos_openblas_root}" _kalos_root_pos)
    if(NOT _kalos_root_pos EQUAL 0)
      message(FATAL_ERROR
        "OpenBLAS_ROOT is authoritative for this build, but ${_kalos_resolved} "
        "points outside it:\n"
        "  OpenBLAS_ROOT:        ${_kalos_openblas_root}\n"
        "  ${_kalos_resolved}: ${_kalos_resolved_path}\n"
        "This mixes a system provider with headers/libraries from another "
        "tree (the header/library mismatch that produces 'undefined symbol: "
        "LAPACKE_*' at import). Unset ${_kalos_resolved} (and any stale value "
        "in the CMake cache) or unset OpenBLAS_ROOT.")
    endif()
    unset(_kalos_resolved_path)
    unset(_kalos_root_pos)
  endforeach()
endif()

include(FindPackageHandleStandardArgs)
find_package_handle_standard_args(KalosOpenBLAS REQUIRED_VARS
  KalosOpenBLAS_INCLUDE_DIR KalosOpenBLAS_LIBRARY)

if(KalosOpenBLAS_FOUND)
  # Probe: the resolved library must link LAPACKE_dpotrf_work as declared by
  # the resolved header. This is the symbol whose absence caused the first
  # baseline wheel to fail at import against Ubuntu's NO_LAPACKE 0.3.26.
  set(_kalos_openblas_probe_src "${CMAKE_CURRENT_LIST_DIR}/kalos_openblas_probe.cpp")
  try_compile(_kalos_openblas_lapacke_ok
    "${CMAKE_CURRENT_BINARY_DIR}/kalos-openblas-probe"
    "${_kalos_openblas_probe_src}"
    CMAKE_FLAGS
      "-DINCLUDE_DIRECTORIES:STRING=${KalosOpenBLAS_INCLUDE_DIR}"
    LINK_LIBRARIES "${KalosOpenBLAS_LIBRARY}"
    OUTPUT_VARIABLE _kalos_openblas_probe_output
  )
  if(NOT _kalos_openblas_lapacke_ok)
    message(FATAL_ERROR
      "OpenBLAS provider probe failed: linking LAPACKE_dpotrf_work failed. "
      "The resolved library does not provide LAPACKE for the resolved "
      "header pair:\n"
      "  header:  ${KalosOpenBLAS_INCLUDE_DIR}/lapacke.h\n"
      "  library: ${KalosOpenBLAS_LIBRARY}\n"
      "A system OpenBLAS without LAPACKE (for example Ubuntu 24.04's "
      "libopenblas-dev 0.3.26) has been resolved against headers that assume "
      "it. Point OpenBLAS_ROOT at one LP64 provider whose lib*/ actually "
      "contains the LAPACKE symbols, or pass an explicit matching "
      "-DKalosOpenBLAS_LIBRARY=.../-DKalosOpenBLAS_INCLUDE_DIR=... pair. "
      "Linker/compiler output:\n${_kalos_openblas_probe_output}")
  endif()
  message(STATUS "KalosOpenBLAS probe OK: LAPACKE_dpotrf_work links against "
    "${KalosOpenBLAS_LIBRARY} with headers from ${KalosOpenBLAS_INCLUDE_DIR}")
endif()

if(KalosOpenBLAS_FOUND AND NOT TARGET Kalos::OpenBLAS)
  add_library(Kalos::OpenBLAS UNKNOWN IMPORTED)
  set_target_properties(Kalos::OpenBLAS PROPERTIES
    IMPORTED_LOCATION "${KalosOpenBLAS_LIBRARY}"
    INTERFACE_INCLUDE_DIRECTORIES "${KalosOpenBLAS_INCLUDE_DIR}")
endif()
