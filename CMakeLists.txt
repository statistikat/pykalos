cmake_minimum_required(VERSION 3.20)
project(pykalos LANGUAGES CXX)
set(KALOS_BUILD_TESTS OFF CACHE BOOL "" FORCE)
option(PYKALOS_BUNDLE_OPENBLAS "Link the pinned OpenBLAS archive privately into the Python module" OFF)
if(PYKALOS_BUNDLE_OPENBLAS)
  include(cmake/BundledOpenBLAS.cmake)
endif()
add_subdirectory(vendor/kalos EXCLUDE_FROM_ALL)
find_package(Python COMPONENTS Interpreter Development.Module REQUIRED)
find_package(pybind11 CONFIG REQUIRED)
pybind11_add_module(_kalos bindings/module.cpp bindings/tramo.cpp bindings/seats.cpp bindings/x13_fixed.cpp)
target_link_libraries(_kalos PRIVATE kalos::kalos)
install(TARGETS _kalos LIBRARY DESTINATION pykalos RUNTIME DESTINATION pykalos)
if(PYKALOS_BUNDLE_OPENBLAS)
  target_compile_definitions(_kalos PRIVATE PYKALOS_BUNDLED_OPENBLAS=1)
  if(APPLE)
    target_link_options(_kalos PRIVATE "LINKER:-exported_symbol,_PyInit__kalos")
  else()
    target_link_options(_kalos PRIVATE "LINKER:--exclude-libs,ALL")
  endif()
  install(FILES vendor/kalos/dependencies/OpenBLAS-LICENSE.txt
                vendor/kalos/dependencies/lapack-netlib-LICENSE.txt
                licenses/GPL-3.0.txt licenses/GCC-Runtime-Library-Exception.txt licenses/LGPL-2.1.txt
                licenses/LLVM-runtime.txt DESTINATION pykalos/licenses)
elseif(UNIX AND NOT APPLE)
  # Linux: embed the resolved OpenBLAS library directory as an install RPATH so
  # the extension loads the same LP64 CBLAS/LAPACKE provider it was linked and
  # qualified against. Some system libopenblas.so.0 builds (e.g. Ubuntu 24.04's
  # 0.3.26 NO_LAPACKE) lack LAPACKE symbols and would fail at import time.
  # Portable wheels that vendor the provider (auditwheel) remain a later task.
  get_directory_property(KalosOpenBLAS_LIBRARY DIRECTORY vendor/kalos DEFINITION KalosOpenBLAS_LIBRARY)
  get_filename_component(_pykalos_openblas_libdir "${KalosOpenBLAS_LIBRARY}" DIRECTORY)
  set_target_properties(_kalos PROPERTIES INSTALL_RPATH "\$ORIGIN;${_pykalos_openblas_libdir}")
endif()
