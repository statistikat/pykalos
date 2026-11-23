# Use the static archive from the same exclusive root as the core's LP64
# header/link probe. Only Python's module initializer should be exported.
if((NOT UNIX AND NOT MINGW) OR NOT OpenBLAS_ROOT)
  message(FATAL_ERROR "PYKALOS_BUNDLE_OPENBLAS needs a POSIX or MinGW build and -DOpenBLAS_ROOT=<pinned provider root>")
endif()
unset(_pykalos_archive CACHE)
find_file(_pykalos_archive libopenblas.a
  PATHS "${OpenBLAS_ROOT}/lib" "${OpenBLAS_ROOT}/lib64" NO_DEFAULT_PATH REQUIRED)
set(KalosOpenBLAS_LIBRARY "${_pykalos_archive}")
find_program(_pykalos_fortran NAMES gfortran REQUIRED)
if(MINGW)
  set(_pykalos_fortran_library libgfortran.dll.a)
else()
  set(_pykalos_fortran_library "libgfortran${CMAKE_SHARED_LIBRARY_SUFFIX}")
endif()
execute_process(COMMAND "${_pykalos_fortran}" "-print-file-name=${_pykalos_fortran_library}"
  OUTPUT_VARIABLE _pykalos_fortran_runtime OUTPUT_STRIP_TRAILING_WHITESPACE COMMAND_ERROR_IS_FATAL ANY)
file(TO_CMAKE_PATH "${_pykalos_fortran_runtime}" _pykalos_fortran_runtime)
if(NOT IS_ABSOLUTE "${_pykalos_fortran_runtime}" OR NOT EXISTS "${_pykalos_fortran_runtime}")
  message(FATAL_ERROR "Cannot locate the shared GNU Fortran runtime for the bundled archive")
endif()
# The core's executable link probes need LAPACK's Fortran runtime too.
string(APPEND CMAKE_CXX_STANDARD_LIBRARIES " \"${_pykalos_fortran_runtime}\"")
list(APPEND CMAKE_TRY_COMPILE_PLATFORM_VARIABLES CMAKE_CXX_STANDARD_LIBRARIES)
