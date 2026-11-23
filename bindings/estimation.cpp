#include <kalos/estimation_control.hpp>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <type_traits>

namespace py = pybind11;
using namespace pybind11::literals;

void bind_estimation(py::module_& module) {
    module.def("_estimate_sarima_fixed", [](const py::dict& spec) {
        kalos::SarimaEstimationRequest request{};
        request.series.values = spec["series"].cast<std::vector<double>>();
        request.series.missing = spec["missing"].cast<std::vector<std::uint8_t>>();
        request.period = spec["period"].cast<int>();
        request.d = spec["d"].cast<int>();
        request.seasonal_d = spec["seasonal_d"].cast<int>();
        request.spec_d = spec["spec_d"].cast<int>();
        request.spec_bd = spec["spec_seasonal_d"].cast<int>();
        request.request_landing_point = spec["request_landing_point"].cast<bool>();
        const auto design = spec["design"].cast<py::dict>();
        const auto columns = design["columns"].cast<std::vector<std::vector<double>>>();
        request.design.columns = columns.size();
        for (const auto& column : columns)
            request.design.values.insert(request.design.values.end(), column.begin(), column.end());
        request.design.coefficients = design["coefficients"].cast<std::vector<double>>();
        request.design.fixed = design["fixed"].cast<std::vector<std::uint8_t>>();
        const char* names[] = {"ar", "ma", "seasonal_ar", "seasonal_ma"};
        const auto blocks = spec["blocks"].cast<py::dict>();
        for (std::size_t i=0; i<request.blocks.size(); ++i) {
            auto block = blocks[names[i]].cast<py::dict>();
            request.blocks[i].initial = block["initial"].cast<std::vector<double>>();
            request.blocks[i].fixed = block["fixed"].cast<std::vector<std::uint8_t>>();
        }
        const auto control = spec["control"].cast<py::dict>();
        const auto start = control["starting_point"].cast<std::string>();
        const auto starting_point = start == "zero" ? kalos::EstimationStartingPoint::Zero :
            start == "default" ? kalos::EstimationStartingPoint::Default :
            start == "hannan_rissanen" ? kalos::EstimationStartingPoint::HannanRissanen :
                                        kalos::EstimationStartingPoint::Multiple;
        request.control = {control["eps"].cast<double>(), control["feps"].cast<double>(),
            control["maximum_likelihood"].cast<bool>(), control["unit_root_search"].cast<bool>(),
            control["corrected_degrees_of_freedom"].cast<bool>(), control["fast_derivatives"].cast<bool>(),
            starting_point, control["solver"].cast<std::string>() == "bfgs" ? kalos::EstimationSolver::Bfgs :
                                                                          kalos::EstimationSolver::PinnedLevenbergMarquardt};
        const auto overrides = spec["optimizer"].cast<py::dict>();
        auto option = [&](const char* name, auto& target) {
            if (overrides.contains(name)) target = overrides[name].cast<std::decay_t<decltype(target)>>();
        };
        auto& optimizer = request.optimizer;
        option("max_iterations", optimizer.max_iterations);
        option("max_evaluations", optimizer.max_evaluations);
        option("max_line_search", optimizer.max_line_search);
        option("difference_refinements", optimizer.difference_refinements);
        option("gradient_tolerance", optimizer.gradient_tolerance);
        option("step_tolerance", optimizer.step_tolerance);
        option("function_tolerance", optimizer.function_tolerance);
        option("difference_step", optimizer.difference_step);
        option("armijo", optimizer.armijo);
        option("max_step", optimizer.max_step);
        kalos::SarimaEstimationResult fit;
        {
            py::gil_scoped_release release;
            fit = kalos::estimate_sarima_fixed(request, [] {
                py::gil_scoped_acquire acquire;
                if (PyErr_CheckSignals() != 0) throw py::error_already_set();
            });
        }
        py::dict coefficients;
        for (std::size_t i=0; i<fit.coefficients.size(); ++i) coefficients[names[i]]=fit.coefficients[i];
        py::list passes;
        for (const auto& pass : fit.passes) {
            passes.append(py::dict("stage"_a=pass.stage, "attempted"_a=pass.attempted,
                "gates_passed"_a=pass.gates_passed, "accepted"_a=pass.accepted,
                "optimizer_status"_a=pass.optimizer_status, "evaluations"_a=pass.evaluations,
                "log_likelihood"_a=pass.log_likelihood, "detail"_a=pass.detail));
        }
        return py::dict("status"_a=fit.status, "converged"_a=fit.converged, "coefficients"_a=coefficients,
                        "log_likelihood"_a=fit.log_likelihood, "has_landing_point"_a=fit.has_landing_point,
                        "passes"_a=passes);
    });
}
