#include "combined_seasonality.hpp"
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <string>
#include <vector>
#include "kalos/x13_fit.hpp"
#include "x11_options.hpp"

namespace py = pybind11;
using namespace pybind11::literals;

namespace {
kalos::X13VariableClass variable_class(const std::string& value) {
    using C = kalos::X13VariableClass;
    if (value == "outlier") return C::outlier;
    if (value == "days_related") return C::days_related;
    if (value == "moving_holiday") return C::moving_holiday;
    if (value == "user") return C::user;
    throw py::value_error("unknown X-13 variable class: " + value);
}

kalos::X13Component component(const std::string& value) {
    using C = kalos::X13Component;
    if (value == "undefined") return C::undefined;
    if (value == "series") return C::series;
    if (value == "trend") return C::trend;
    if (value == "seasonal") return C::seasonal;
    if (value == "seasonally_adjusted") return C::seasonally_adjusted;
    if (value == "irregular") return C::irregular;
    if (value == "calendar_effect") return C::calendar_effect;
    throw py::value_error("unknown X-13 regression effect: " + value);
}

kalos::X13FitRequest read_request(const py::dict& spec) {
    using namespace pykalos_options;
    kalos::X13FitRequest request;
    request.input = spec["series"].cast<std::vector<double>>();
    for (py::handle item : spec["variables"].cast<py::list>()) {
        const auto variable = item.cast<py::dict>();
        request.variables.push_back({
            variable_class(variable["class"].cast<std::string>()),
            component(variable["effect"].cast<std::string>()),
            variable["coefficient"].cast<std::vector<double>>(),
            variable["columns"].cast<std::vector<std::vector<double>>>()
        });
    }
    request.log = spec["log"].cast<bool>();
    request.frequency = spec["frequency"].cast<int>();
    request.first_period = spec["start_period"].cast<int>();
    for (const auto& name : spec["seasonal"].cast<std::vector<std::string>>())
        request.seasonal.push_back(seasonal_from_name(name));
    request.trend_length = spec["trend_length"].cast<int>();
    if (!spec["sigma"].is_none()) request.sigma = sigma_from_name(spec["sigma"].cast<std::string>());
    request.lower_sigma = spec["lower_sigma"].cast<double>();
    request.upper_sigma = spec["upper_sigma"].cast<double>();
    request.msr_policy = msr_from_name(spec["msr_policy"].cast<std::string>());
    request.mode = mode_from_name(spec["mode"].cast<std::string>());
    request.backcast = spec["backcast"].cast<int>();
    request.forecast = spec["forecast"].cast<int>();
    return request;
}

py::dict fit_result(const kalos::X13FitResult& result) {
    using namespace pykalos_options;
    py::list seasonal;
    for (const auto filter : result.seasonal) seasonal.append(seasonal_name(filter));
    py::dict out("status"_a=result.status, "available"_a=(result.status == "available"),
                 "frequency"_a=result.frequency, "start_period"_a=result.first_period,
                 "mode_requested"_a=mode_name(result.mode_requested),
                 "mode_effective"_a=mode_name(result.mode_effective), "log"_a=result.log,
                 "seasonal"_a=seasonal, "trend_length"_a=result.trend_length,
                 "sigma_set"_a=result.sigma_set, "sigma"_a=sigma_name(result.sigma),
                 "lower_sigma"_a=result.lower_sigma, "upper_sigma"_a=result.upper_sigma,
                 "msr_policy"_a=msr_policy_name(result.msr_policy),
                 "backcast"_a=result.backcast, "forecast"_a=result.forecast);
    out["diagnostics"] = pykalos_diagnostics::seasonality(kalos::x13_si_seasonality(result));
    const auto& p = result.preadjustment;
    if (!p.status.empty()) {
        out["preadjustment"] = py::dict(
            "a1"_a=p.a1, "a6"_a=p.a6, "a7"_a=p.a7, "a8"_a=p.a8, "a8t"_a=p.a8t,
            "a8s"_a=p.a8s, "a8i"_a=p.a8i, "a9"_a=p.a9, "a9u"_a=p.a9u,
            "a9cal"_a=p.a9cal, "a9sa"_a=p.a9sa, "a9ser"_a=p.a9ser, "out"_a=p.out);
    }
    const auto& selection = result.selection;
    if (!selection.status.empty()) {
        out["selection"] = py::dict("status"_a=selection.status, "initial_filters"_a=selection.initial_filters,
                                    "final_filters"_a=selection.final_filters, "trend_length"_a=selection.final.length);
    }
    if (result.status == "available") {
        out["results"] = py::dict("d10"_a=result.d10, "d11"_a=result.d11, "d12"_a=result.d12,
                                  "d13"_a=result.d13, "c17"_a=result.c17);
        const auto& f = result.finals;
        out["finals"] = py::dict("d11final"_a=f.d11final, "d12final"_a=f.d12final,
                                 "d13final"_a=f.d13final, "d16"_a=f.d16, "d18"_a=f.d18,
                                 "e1"_a=f.e1, "e2"_a=f.e2, "e3"_a=f.e3, "e11"_a=f.e11);
        out["finalSA"] = result.finalSA;
        out["finalTrend"] = result.finalTrend;
        out["finalIrregular"] = result.finalIrregular;
    }
    return out;
}
}  // namespace

void bind_restricted_x13(py::module_& module) {
    module.def("_x13_fixed", [](const py::dict& normalized) {
        const auto request = read_request(normalized);
        kalos::X13FitResult result;
        {
            py::gil_scoped_release release;
            result = kalos::x13_fit(request);
        }
        return fit_result(result);
    });
}
