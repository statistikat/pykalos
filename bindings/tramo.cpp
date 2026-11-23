#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <utility>
#include "kalos/tramo_transform_decision.hpp"
#include "kalos/tramo_calendar_f_test.hpp"

namespace py = pybind11;
using namespace pybind11::literals;

namespace {
py::dict test_report(const kalos::TramoSeasonalityTest& test) {
    return py::dict("value"_a=test.value, "p_value"_a=test.p_value, "valid"_a=test.valid);
}

py::dict seasonality_report(const kalos::TramoSeasonalityReport& report) {
    return py::dict("verdict"_a=report.verdict, "to_int"_a=report.to_int,
                    "qs"_a=test_report(report.qs), "friedman"_a=test_report(report.friedman),
                    "differenced"_a=report.differenced);
}
}  // namespace

void bind_tramo_preprocessing(py::module_& module) {
    module.def("_tramo_critical_value", &kalos::tramo_critical_value);
    module.def("_tramo_calendar_f_test", [](const std::vector<double>& values, int year, int month,
            bool mean, double significance, double precision) {
        kalos::TramoCalendarFTestResult result;
        {
            py::gil_scoped_release release;
            result = kalos::tramo_calendar_f_test(values, year, month, mean, significance, precision);
        }
        auto report = [](const kalos::TramoCalendarFCandidate& fit) {
            return py::dict("residual_ssq"_a=fit.residual_ssq, "degrees_of_freedom"_a=fit.degrees_of_freedom,
                            "mean_square"_a=fit.mean_square, "lower_probability"_a=fit.lower_probability);
        };
        const char* selected = "none";
        if (result.selected == kalos::TramoTradingDays::WorkingDays) selected = "working_days";
        if (result.selected == kalos::TramoTradingDays::TradingDays) selected = "trading_days";
        return py::dict("base_ssq"_a=result.base_ssq, "working_days"_a=report(result.working_days),
                        "trading_days"_a=report(result.trading_days), "selected"_a=selected);
    });
    module.def("_tramo_seasonality", [](const std::vector<double>& values) {
        kalos::TramoSeasonalityReport report;
        {
            py::gil_scoped_release release;
            report = kalos::tramo_seasonality(values);
        }
        return seasonality_report(report);
    });
    module.def("_tramo_transform_decision", [](std::vector<double> values, double log_preference,
            double precision, bool mean, bool detect_seasonality, bool spec_seasonality) {
        kalos::TramoTransformDecisionRequest request;
        request.values = std::move(values);
        request.period = 12;
        request.mean = mean;
        request.detect_seasonality = detect_seasonality;
        request.spec_seasonality = spec_seasonality;
        request.log_preference = log_preference;
        request.precision = precision;
        kalos::TramoTransformDecisionResult result;
        {
            py::gil_scoped_release release;
            result = kalos::decide_tramo_transform(request);
        }
        py::object detector = py::none();
        if (detect_seasonality) detector = seasonality_report(result.seasonality);
        return py::dict("seasonality"_a=detector, "spec_pre"_a=result.spec_pre,
                        "seasonal"_a=result.seasonal, "nonpositive"_a=result.nonpositive,
                        "loglevel_status"_a=result.loglevel_status, "choosing_log"_a=result.choosing_log,
                        "log_ll"_a=result.log_ll, "level_ll"_a=result.level_ll,
                        "log_correction"_a=result.log_correction, "log_preference"_a=result.log_preference,
                        "log_transform"_a=result.log_transform, "remarks"_a=result.remarks);
    });
}
