cmake_minimum_required(VERSION 3.20)
project(pykalos LANGUAGES CXX)
set(KALOS_BUILD_TESTS OFF CACHE BOOL "" FORCE)
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
  get_directory_property(KalosOpenBLAS_LIBRARY DIRECTORY vendor/kalos DEFINITION KalosOpenBLAS_LIBRARY)
  get_filename_component(_pykalos_openblas_libdir "${KalosOpenBLAS_LIBRARY}" DIRECTORY)
  set_target_properties(_kalos PROPERTIES INSTALL_RPATH "\$ORIGIN;${_pykalos_openblas_libdir}")
endif()
