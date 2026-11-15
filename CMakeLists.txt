cmake_minimum_required(VERSION 3.20)
project(pykalos LANGUAGES CXX)
set(KALOS_BUILD_TESTS OFF CACHE BOOL "" FORCE)
# Resolve the OpenBLAS provider with pykalos's hardened finder (cmake/) before
# the vendored core runs its own find_package(KalosOpenBLAS REQUIRED). The core
# snapshot prepends vendor/kalos/cmake to CMAKE_MODULE_PATH and must not be
# edited, so pre-finding here is what shadows its FindKalosOpenBLAS.cmake: the
# snapshot's call short-circuits on the cached KalosOpenBLAS_FOUND and reuses
# the Kalos::OpenBLAS target created at this (parent) scope. The hardened
# finder makes -DOpenBLAS_ROOT authoritative over pkg-config/system paths and
# probe-links LAPACKE_dpotrf_work at configure time, so a header/library mix
# fails loudly instead of as an undefined symbol at import.
list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")
find_package(KalosOpenBLAS REQUIRED)
add_subdirectory(vendor/kalos EXCLUDE_FROM_ALL)
find_package(Python COMPONENTS Interpreter Development.Module REQUIRED)
find_package(pybind11 CONFIG REQUIRED)
pybind11_add_module(_kalos bindings/module.cpp)
target_link_libraries(_kalos PRIVATE kalos::kalos)
install(TARGETS _kalos LIBRARY DESTINATION pykalos RUNTIME DESTINATION pykalos)
if(UNIX AND NOT APPLE)
  # Linux: embed the resolved OpenBLAS library directory as an install RPATH so
  # the extension loads the same LP64 CBLAS/LAPACKE provider it was linked and
  # qualified against. Some system libopenblas.so.0 builds (e.g. Ubuntu 24.04's
  # 0.3.26 NO_LAPACKE) lack LAPACKE symbols and would fail at import time.
  # Portable wheels that vendor the provider (auditwheel) remain a later task.
  get_filename_component(_pykalos_openblas_libdir "${KalosOpenBLAS_LIBRARY}" DIRECTORY)
  set_target_properties(_kalos PROPERTIES INSTALL_RPATH "\$ORIGIN;${_pykalos_openblas_libdir}")
endif()
