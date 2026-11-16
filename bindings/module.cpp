#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "kalos/numerics.hpp"
#include "kalos/version.hpp"
#include "kalos/parallel.hpp"
#include "kalos/detail/lapack.hpp"
namespace py = pybind11;
PYBIND11_MODULE(_kalos, m) {
    m.doc() = "Minimal owned-buffer Kalos bindings";
    m.def("core_version", [] {
        py::dict result;
        result["version"] = kalos::version;
        result["commit"] = kalos::core_revision;
        result["provider"] = kalos::lapack::provider_name();
        result["provider_version"] = kalos::lapack::provider_version();
        result["blas_integer_bits"] = 32;
        result["openmp"] = kalos::parallel_info().compiled;
        return result;
    });
    m.def("capabilities", [] {
        py::dict result;
        result["fit"] = false;
        result["primitives"] = py::make_tuple("convolve");
        result["status"] = "minimal_binding";
        return result;
    });
    m.def("convolve", [](std::vector<double> left, std::vector<double> right) {
        // Inputs are owned before releasing the GIL. The core invokes callbacks
        // on the caller only; Python APIs never run in an OpenMP worker.
        py::gil_scoped_release release;
        return kalos::convolve(left, right, [] {
            py::gil_scoped_acquire acquire;
            if (PyErr_CheckSignals() != 0) throw py::error_already_set();
        });
    }, py::arg("left"), py::arg("right"),
        "Multiply lag polynomials using owned C++ buffers.\n"
        "\n"
        "Boundary semantics (qualified in M2, see IMPLEMENTATION_STATUS.md):\n"
        "both arguments accept any 1-D numeric vector: Python sequences and\n"
        "iterables (per-element conversion, so lists of ints are fine),\n"
        "NumPy arrays and views - float64 or narrower, contiguous,\n"
        "strided or negative-strided, read-only buffers included - and\n"
        "memoryviews. 2-D/0-D inputs, bytes and str raise TypeError.\n"
        "Inputs are always copied into owned vectors before the GIL is\n"
        "released (copy-in: caller memory can never alias the lock-free\n"
        "computation); masked arrays are rejected because NumPy converts\n"
        "masked elements to NaN and the core refuses non-finite\n"
        "coefficients. NaN/Inf and empty inputs propagate the core's\n"
        "ValueError policy unchanged. The result is always a Python list.");
}
