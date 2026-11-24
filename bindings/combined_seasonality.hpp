#pragma once

#include <kalos/combined_seasonality.hpp>
#include <pybind11/pybind11.h>

namespace pykalos_diagnostics {

inline pybind11::dict seasonality(const std::optional<kalos::CombinedSiSeasonality>& result) {
    namespace py = pybind11;
    using namespace pybind11::literals;
    if (!result) return py::dict("combined_seasonality"_a=py::none());
    auto statistic = [](double value, double p) {
        return py::dict("value"_a=value, "pvalue"_a=p);
    };
    return py::dict("combined_seasonality"_a=py::dict("summary"_a=result->summary,
        "stable"_a=statistic(result->stable_f, result->stable_p),
        "moving"_a=statistic(result->moving_f, result->moving_p),
        "kruskal_wallis"_a=statistic(result->kruskal_wallis, result->kruskal_p)));
}

} // namespace pykalos_diagnostics
