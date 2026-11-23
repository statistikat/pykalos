#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <kalos/tramo_seats_pipeline.hpp>
#include <kalos/arma_diagnostics.hpp>
#include <kalos/numerics.hpp>
#include <optional>

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

py::dict airline_residuals(int year, int month, const std::vector<double>& values, double standard_error) {
    kalos::LjungBoxTest lb;
    std::optional<kalos::ResidualNormalityTest> normality;
    {
        py::gil_scoped_release release;
        lb = kalos::monthly_airline_residual_ljung_box(values);
        normality = kalos::tramo_residual_normality(values);
    }
    py::object dh = py::none();
    if (normality) dh = py::dict("value"_a=normality->value, "pvalue"_a=normality->p, "df"_a=normality->df);
    return py::dict("start_year"_a=year, "start_month"_a=month, "tsres"_a=values,
                    "ser"_a=standard_error, "doornikhansen"_a=dh,
                    "lb"_a=py::dict("value"_a=lb.value, "pvalue"_a=lb.p, "df"_a=lb.df, "lags"_a=24));
}

py::dict tr1_preprocessing(const kalos::TramoFitResult& fit) {
    py::dict result("status"_a=fit.status);
    if (fit.status != "available") {
        result["refusal_note"] = fit.refusal_note;
        return result;
    }
    const auto& o = fit.orders;
    py::dict model("orders"_a=py::dict("p"_a=o.p, "d"_a=o.d, "q"_a=o.q, "bp"_a=o.bp, "bd"_a=o.bd, "bq"_a=o.bq),
                   "log"_a=fit.log, "mean_correction"_a=fit.mean);
    // Fit parameters are in JVM order, with regular and seasonal AR preceding MA.
    const std::pair<const char*, int> sizes[] = {{"phi", o.p}, {"bphi", o.bp}, {"theta", o.q}, {"btheta", o.bq}};
    std::size_t offset = 0;
    for (const auto& [name, count] : sizes) {
        const auto length = static_cast<std::size_t>(count);
        if (length > fit.parameters.size() - offset) throw std::logic_error("incomplete fitted TRAMO model");
        model[name] = std::vector<double>(fit.parameters.begin() + offset, fit.parameters.begin() + offset + length);
        offset += length;
    }
    if (offset != fit.parameters.size()) throw std::logic_error("unexpected fitted TRAMO parameters");
    result["model"] = std::move(model);
    py::list variables;
    static constexpr const char* types[] = {"AO", "LS", "TC", "SO"};
    if (fit.mean) variables.append(py::dict("name"_a="const", "coefficient"_a=fit.regression_coefficients.at(0)));
    for (std::size_t i = 0; i < fit.variables.size(); ++i) {
        const auto& variable = fit.variables[i];
        variables.append(py::dict("name"_a=variable.name, "type"_a=types[static_cast<int>(variable.type)],
                                  "position"_a=variable.position,
                                  "coefficient"_a=fit.regression_coefficients.at(i + static_cast<std::size_t>(fit.mean))));
    }
    result["variables"] = std::move(variables);
    result["likelihood"] = py::dict("log_likelihood"_a=fit.ls_ll, "transformation_adjustment"_a=fit.ls_tadj,
                                    "adjusted_log_likelihood"_a=fit.ls_all, "ssq"_a=fit.ls_ssq,
                                    "effective"_a=fit.ls_eff, "estimated"_a=fit.ls_npar);
    const auto& b = fit.builder;
    const auto start = kalos::TimeDomain(b.domain_year, b.domain_position + 1, 12, b.domain_length)
                           .at(b.domain_length - fit.ls_eff);
    const double ser = kalos::tramo_residual_standard_error(fit.ls_ssq, fit.ls_eff, fit.ls_npar);
    result["residuals"] = airline_residuals(start.first, start.second, fit.full_residuals, ser);
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
    module.def("_estimate_tramo_tr1", [](const std::vector<double>& series, int year, int month) {
        kalos::TramoFitResult fit;
        {
            py::gil_scoped_release release;
            fit = kalos::estimate_tramo_tr1(series, year, month);
        }
        return tr1_preprocessing(fit);
    });
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
            variable.type = static_cast<kalos::TramoOutlierKind>(row["type"].cast<int>());
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
    module.def("_tramoseats_rsa1", [](const std::vector<double>& series, int year, int month,
                                      int backcast, int forecast) {
        kalos::tramo_seats_automatic_result output;
        kalos::tramo_tr0_forecast_errors_result errors;
        {
            py::gil_scoped_release release;
            output = kalos::run_tramo_seats_rsa1(series, year, month, backcast, forecast);
            errors = kalos::tramo_tr1_forecast_errors(output.preprocessing, forecast);
        }
        auto result = tr1_preprocessing(output.preprocessing);
        result["series_forecast_stdev_status"] = errors.status;
        result["series_forecast_stdev"] = errors.standard_errors;
        result["preprocessing_status"] = result["status"];
        result.attr("update")(decomposition(output.decomposition));
        result["model_changed"] = output.decomposition.extraction.model_changed;
        return result;
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
        result["residuals"] = airline_residuals(residuals.start_year, residuals.start_month,
                                               residuals.values, residuals.standard_error);
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
