#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <kalos/tramo_seats_pipeline.hpp>

namespace py = pybind11;
using namespace pybind11::literals;

namespace {
py::list components(const std::vector<kalos::seats_component_series>& rows) {
    static constexpr const char* types[] = {"Series", "Trend", "Seasonal", "SeasonallyAdjusted", "Irregular", "CalendarEffect"};
    static constexpr const char* information[] = {"Value", "Stdev", "Forecast", "StdevForecast", "Backcast", "StdevBackcast"};
    py::list result;
    for (const auto& row : rows) {
        result.append(py::dict("component"_a=types[static_cast<int>(row.component)],
            "information"_a=information[static_cast<int>(row.information)],
            "start_year"_a=row.start_year, "start_month"_a=row.start_month, "values"_a=row.values));
    }
    return result;
}

py::dict extraction(const kalos::seats_extract_wk_result& wk) {
    return py::dict("status"_a=wk.fact("status"), "initial"_a=components(wk.initial_components()),
                    "final"_a=components(wk.final_components()));
}

py::dict decomposition(const kalos::tramo_seats_pipeline_result& output) {
    auto result = extraction(output.extraction);
    result["merged"] = components(output.finals);
    return result;
}

kalos::tramo_seats_model_request model(std::vector<double> series, const py::dict& spec) {
    kalos::tramo_seats_model_request request;
    request.series = std::move(series);
    request.frequency = request.period = spec["frequency"].cast<int>();
    request.start_year = spec["start_year"].cast<int>();
    request.start_month = spec["start_month"].cast<int>();
    request.d = spec["d"].cast<int>();
    request.bd = spec["bd"].cast<int>();
    request.log = spec["log"].cast<bool>();
    request.mean_correction = spec["mean_correction"].cast<bool>();
    request.phi = spec["phi"].cast<std::vector<double>>();
    request.bphi = spec["bphi"].cast<std::vector<double>>();
    request.theta = spec["theta"].cast<std::vector<double>>();
    request.btheta = spec["btheta"].cast<std::vector<double>>();
    request.forecast_count = spec["forecast"].cast<int>();
    request.backcast_count = spec["backcast"].cast<int>();
    return request;
}
}

void bind_seats(py::module_& module) {
    module.def("_seats_extract_wk", [](std::vector<double> series, const py::dict& spec) {
        auto request = model(std::move(series), spec);
        request.innovation_variance = spec["innovation_variance"].cast<double>();
        request.xl = spec["xl"].cast<double>();
        request.epsphi = spec["epsphi"].cast<double>();
        request.rmod = spec["rmod"].cast<double>();
        request.smod = spec["smod"].cast<double>();
        request.smod_pi = spec["smod_pi"].cast<double>();
        const auto approximation = spec["approximation"].cast<std::string>();
        request.mode = approximation == "none" ? kalos::seats_approx_mode::none :
            approximation == "legacy" ? kalos::seats_approx_mode::legacy : kalos::seats_approx_mode::noisy;
        request.components_method = spec["method"].cast<std::string>() == "burman" ?
            kalos::seats_components_method::burman : kalos::seats_components_method::kalman_smoother;
        request.bias = spec["bias"].cast<std::string>() == "legacy" ?
            kalos::seats_bias_correction::legacy : kalos::seats_bias_correction::none;
        kalos::seats_extract_wk_result result;
        {
            py::gil_scoped_release release;
            result = kalos::seats_extract_wk(request);
        }
        return extraction(result);
    });
    module.def("_seats_from_tramo", [](std::vector<double> series, const py::dict& spec) {
        auto request = model(std::move(series), spec);
        kalos::TramoFitResult fit;
        fit.status = "available";
        auto& builder = fit.builder;
        builder.annual_frequency = request.frequency;
        builder.domain_year = builder.estimation_year = request.start_year;
        builder.domain_position = builder.estimation_position = request.start_month - 1;
        builder.domain_length = builder.estimation_length = static_cast<int>(request.series.size());
        builder.interpolated = std::move(request.series);
        fit.orders.d = request.d;
        fit.orders.bd = request.bd;
        auto append = [&](int& order, const std::vector<double>& values) {
            order = static_cast<int>(values.size());
            fit.parameters.insert(fit.parameters.end(), values.begin(), values.end());
        };
        append(fit.orders.p, request.phi);
        append(fit.orders.bp, request.bphi);
        append(fit.orders.q, request.theta);
        append(fit.orders.bq, request.btheta);
        fit.log = request.log;
        fit.mean = request.mean_correction;
        fit.ls_ssq = spec["ssq"].cast<double>();
        fit.ls_eff = spec["effective"].cast<int>();
        fit.ls_npar = spec["estimated"].cast<int>();
        for (const auto& item : spec["outliers"].cast<py::list>()) {
            const auto row = item.cast<py::dict>();
            kalos::TramoFitVariable variable;
            variable.type = row["type"].cast<std::string>() == "AO" ? kalos::TramoOutlierKind::Ao : kalos::TramoOutlierKind::Ls;
            variable.position = row["position"].cast<int>();
            variable.coefficient = row["coefficient"].cast<double>();
            fit.variables.push_back(variable);
        }
        kalos::tramo_seats_pipeline_result result;
        {
            py::gil_scoped_release release;
            result = kalos::run_tramo_seats_pipeline(fit, request.backcast_count, request.forecast_count);
        }
        return decomposition(result);
    });
    module.def("_tramoseats_rsa0", [](const std::vector<double>& series, int year, int month,
                                      int backcast, int forecast) {
        kalos::tramo_seats_rsa0_result output;
        kalos::tramo_tr0_forecast_errors_result errors;
        {
            py::gil_scoped_release release;
            output = kalos::run_tramo_seats_rsa0(series, year, month, backcast, forecast);
            errors = kalos::tramo_tr0_forecast_errors(output.preprocessing, forecast);
        }
        auto result = decomposition(output.decomposition);
        result["series_forecast_stdev_status"] = errors.status;
        result["series_forecast_stdev"] = errors.standard_errors;
        const auto& fit = output.preprocessing;
        const auto& model = fit.model;
        const auto& residuals = fit.residuals;
        result["residuals"] = py::dict("start_year"_a=residuals.start_year, "start_month"_a=residuals.start_month,
                                      "tsres"_a=residuals.values, "ser"_a=residuals.standard_error);
        result["model"] = py::dict(
            "orders"_a=py::dict("p"_a=model.phi.size(), "d"_a=model.d, "q"_a=model.theta.size(),
                                "bp"_a=model.bphi.size(), "bd"_a=model.bd, "bq"_a=model.btheta.size()),
            "phi"_a=model.phi, "bphi"_a=model.bphi, "theta"_a=model.theta, "btheta"_a=model.btheta,
            "log"_a=model.log, "mean_correction"_a=model.mean_correction,
            "mean_coefficient"_a=fit.mean_coefficient, "innovation_variance"_a=model.innovation_variance);
        result["likelihood"] = py::dict("log_likelihood"_a=fit.log_likelihood, "ssq"_a=fit.residual_ssq,
            "effective"_a=fit.effective_observations, "estimated"_a=fit.estimated_parameters);
        return result;
    });
}
