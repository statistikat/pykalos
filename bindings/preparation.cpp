#include <kalos/preparation.hpp>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;
using namespace pybind11::literals;

namespace {
py::dict domain_record(const kalos::TimeDomain& domain) {
    const auto [year, period] = domain.at(0);
    return py::dict("start"_a=py::make_tuple(year, period), "frequency"_a=domain.frequency(),
                    "length"_a=domain.length());
}

py::list columns(const std::vector<double>& values, std::size_t count, std::size_t rows) {
    py::list result;
    for (std::size_t col=0; col<count; ++col) {
        auto begin = values.begin() + col * rows;
        result.append(std::vector<double>(begin, begin + rows));
    }
    return result;
}

using Date = std::pair<std::int64_t,int>;
using Regressor = std::tuple<std::string, Date, std::vector<double>>;
using Coefficient = std::tuple<std::string,double,bool>;

std::optional<std::int64_t> ordinal(const std::optional<Date>& date, int frequency) {
    if (!date) return std::nullopt;
    return kalos::TimeDomain(date->first, date->second, frequency, 1).start_ordinal();
}
}

void bind_preparation(py::module_& m) {
    m.def("_prepare_series", [](std::vector<double> values, std::vector<std::uint8_t> missing, bool logarithm,
                                std::size_t degree, std::size_t source_offset) {
        kalos::MaskedSeries series{std::move(values), std::move(missing)};
        const auto transform = logarithm ? kalos::Transform::logarithm : kalos::Transform::none;
        kalos::TransformedSeries transformed;
        kalos::LikelihoodAdjustment adjustment;
        {
            py::gil_scoped_release release;
            transformed = kalos::transform_series(series, transform);
            adjustment = kalos::likelihood_adjustment(transformed.log_jacobian, transform, degree, source_offset);
        }
        return py::dict("values"_a=transformed.series.values, "log_jacobian_terms"_a=adjustment.terms,
                        "log_jacobian"_a=adjustment.log_jacobian, "local_rows"_a=adjustment.local_rows,
                        "source_rows"_a=adjustment.source_rows);
    });
    m.def("_prepare_regression", [](std::int64_t length, Date start, int frequency,
          std::optional<Date> first, std::optional<Date> last, std::vector<Regressor> inputs,
          const std::vector<Coefficient>& coefficients, int d, int seasonal_d,
          double mean, bool include_mean, bool include_drift, int backcasts, int forecasts) {
        const kalos::TimeDomain source(start.first, start.second, frequency, length);
        const auto window = kalos::estimation_window(source, ordinal(first, frequency), ordinal(last, frequency));
        std::vector<kalos::NamedRegressor> regressors;
        for (auto& [name, date, values] : inputs) {
            kalos::TimeDomain domain(date.first, date.second, frequency, values.size());
            regressors.push_back({name, domain, std::move(values)});
        }
        std::vector<kalos::NamedCoefficient> spec;
        for (const auto& [name, value, fixed] : coefficients)
            spec.push_back({name, value, fixed});
        auto output = [&] {
            py::gil_scoped_release release;
            auto aligned = kalos::align_regressors(window.domain, regressors, backcasts, forecasts);
            return kalos::prepare_regression(std::move(aligned), spec, d, seasonal_d, mean,
                                             include_mean, include_drift, window.first);
        }();
        const auto& aligned = output.regressors;
        const auto& design = output.design;
        py::list fixed;
        for (auto value : design.fixed) fixed.append(bool(value));
        return py::dict("observed"_a=domain_record(aligned.observed), "required"_a=domain_record(aligned.required),
            "source_offset"_a=window.first, "observed_offset"_a=aligned.observed_offset,
            "names"_a=aligned.names, "generated"_a=output.generated,
            "columns"_a=columns(aligned.values, aligned.names.size(), aligned.required.length()),
            "design"_a=py::dict("columns"_a=columns(design.values, design.columns, aligned.observed.length()),
                                "coefficients"_a=design.coefficients, "fixed"_a=fixed));
    });
}
