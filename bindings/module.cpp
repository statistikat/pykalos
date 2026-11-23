#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <algorithm>
#include <cstdint>
#include <optional>
#include <string>
#include <vector>
#include "kalos/numerics.hpp"
#include "kalos/version.hpp"
#include "kalos/parallel.hpp"
#include "kalos/detail/lapack.hpp"
#include "kalos/x13_automatic.hpp"
#include "x11_options.hpp"
namespace py = pybind11;
void bind_restricted_x13(py::module_& module);
void bind_preparation(py::module_& module);
void bind_estimation(py::module_& module);
void bind_seats(py::module_& module);
void bind_tramo_preprocessing(py::module_& module);

namespace {
using namespace pykalos_options;

// ---- enum name mirrors (boundary vocabulary; never re-decided in Python) ----

int outlier_code(kalos::OutlierType t) { return static_cast<int>(t); }

kalos::OutlierType outlier_from_code(long v) {
    switch (v) {
        case 0: return kalos::OutlierType::Additive;
        case 1: return kalos::OutlierType::LevelShift;
        case 2: return kalos::OutlierType::TransitoryChange;
        case 3: return kalos::OutlierType::SeasonalOutlier;
        default: throw py::value_error("unknown outlier type code: " + std::to_string(v));
    }
}

// ---- request builders (fail-closed on any missing / unknown field) ---------
//
// REVIEW-1 boundary contract: every field is read with an explicit type
// check and a message naming the field and the offending type. Unknown keys
// are reported naming them (a misspelled optional option, e.g.
// use_calender_detection, never silently vanishes); integer fields must
// implement __index__ (no float truncation, no bool-as-int); flags must be
// real Python bools (the string "False" must never mean True); the two
// outlier budgets are sign-checked before the size_t conversion; the series
// is refused as text/binary/multivariate before the core sees it. This
// parser adds NO policy about CONTENT: well-formed but unsupported requests
// still reach the core and keep its documented status responses.

const char* const kRequiredRequestKeys[] = {
    "input", "frequency", "first_year", "first_period", "aicc_log_correction",
    "max_d", "max_bd", "ub1", "ub2", "cancel", "differencing_precision",
    "models_count", "max_p", "max_q", "max_bp", "max_bq", "balanced", "mixed",
    "arma_accept_white_noise", "arma_eps", "outliers_used", "outlier_types",
    "outlier_max_round", "outlier_max_outliers", "tcrate", "precision",
    "mean_precision", "va", "reduce_va", "ljung_box_limit", "check_mu",
    "accept_airline", "ur_limit", "mean_test_initial", "mean_test_final",
    "tsig", "seasonal", "trend_length", "msr_policy", "mode", "backcast",
    "forecast", "lower_sigma", "upper_sigma",
};
const char* const kOptionalRequestKeys[] = {
    "outlier_span", "sigma", "use_calendar_detection", "use_easter_detection",
    "automatic_trading_days", "use_user_variables",
};

bool key_in(const std::string& key, const char* const* list, std::size_t n) {
    for (std::size_t i = 0; i < n; ++i)
        if (key == list[i]) return true;
    return false;
}

bool is_text(py::handle obj) {
    return PyUnicode_Check(obj.ptr()) || PyBytes_Check(obj.ptr())
        || PyByteArray_Check(obj.ptr());
}

bool is_complex(py::handle value) {
    if (PyComplex_Check(value.ptr())) return true;
    if (PyFloat_Check(value.ptr()) || PyLong_Check(value.ptr())) return false;
    const auto dtype = py::getattr(value, "dtype", py::none());
    return py::str(py::getattr(dtype, "kind", py::none())).equal(py::str("c"));
}

std::vector<double> real_coefficients(py::handle values) {
    if (PyUnicode_Check(values.ptr()) || PyBytes_Check(values.ptr()) || PyDict_Check(values.ptr()))
        throw py::type_error("convolve expects a sequence of real coefficients");
    auto iterator = py::iter(values);
    std::vector<double> result;
    const auto size = PyObject_LengthHint(values.ptr(), 0);
    if (size < 0) throw py::error_already_set();
    result.reserve(static_cast<std::size_t>(size));
    for (const auto item : iterator) {
        if (is_complex(item))
            throw py::type_error("convolve coefficients must be real; complex values are refused");
        try {
            result.push_back(item.cast<double>());
        } catch (const py::cast_error&) {
            throw py::type_error("convolve coefficients must be real scalar numbers");
        }
    }
    return result;
}

std::string type_name(py::handle obj) { return obj.ptr()->ob_type->tp_name; }

void validate_request_keys(const py::dict& d) {
    std::vector<std::string> unknown;
    for (const auto& item : d) {
        if (!PyUnicode_Check(item.first.ptr()))
            throw py::type_error("x13_automatic_fit request keys must be strings, got type "
                                 + type_name(item.first));
        const std::string key = py::cast<std::string>(item.first);
        if (!key_in(key, kRequiredRequestKeys, std::size(kRequiredRequestKeys))
            && !key_in(key, kOptionalRequestKeys, std::size(kOptionalRequestKeys)))
            unknown.push_back(key);
    }
    if (unknown.empty()) return;
    std::sort(unknown.begin(), unknown.end());
    std::string joined;
    for (const auto& k : unknown) {
        if (!joined.empty()) joined += ", ";
        joined += k;
    }
    throw py::type_error("x13_automatic_fit request contains unknown key(s): " + joined
                         + "; every key must be part of the raw request schema — a "
                           "misspelled optional option is never silently ignored");
}

py::object req_value(const py::dict& d, const char* key) {
    if (!d.contains(key)) throw py::key_error(std::string("x13_automatic request missing field: ") + key);
    return py::reinterpret_borrow<py::object>(d[py::str(key)]);
}

template <typename T>
T req_int(const py::dict& d, const char* key) {
    py::object v = req_value(d, key);
    if (PyBool_Check(v.ptr()) || !PyIndex_Check(v.ptr()))
        throw py::type_error(std::string("x13_automatic request field '") + key
                             + "' must be an integer (bool and float are refused, no truncation), got type "
                             + type_name(v));
    PyObject* as_long = PyNumber_Index(v.ptr());
    if (!as_long) throw py::error_already_set();
    return py::cast<T>(py::reinterpret_steal<py::object>(as_long));  // range-checked
}

bool req_bool(const py::dict& d, const char* key) {
    py::object v = req_value(d, key);
    if (!PyBool_Check(v.ptr()))
        throw py::type_error(std::string("x13_automatic request field '") + key
                             + "' must be a Python bool (True/False); got type " + type_name(v)
                             + " — truthiness is never a decision input");
    return py::cast<bool>(v);
}

bool req_opt_bool(const py::dict& d, const char* key, bool fallback) {
    if (!d.contains(key)) return fallback;
    py::object v = py::reinterpret_borrow<py::object>(d[py::str(key)]);
    if (v.is_none()) return fallback;
    if (!PyBool_Check(v.ptr()))
        throw py::type_error(std::string("x13_automatic request field '") + key
                             + "' must be a Python bool (True/False) or None; got type "
                             + type_name(v) + " — truthiness is never a decision input");
    return py::cast<bool>(v);
}

double req_double(const py::dict& d, const char* key) {
    py::object v = req_value(d, key);
    if (PyBool_Check(v.ptr()) || is_text(v) || is_complex(v))
        throw py::type_error(std::string("x13_automatic request field '") + key
                             + "' must be a real number (bool and text are refused), got type "
                             + type_name(v));
    double out = PyFloat_AsDouble(v.ptr());
    if (out == -1.0 && PyErr_Occurred()) {
        PyErr_Clear();
        throw py::type_error(std::string("x13_automatic request field '") + key
                             + "' must be a real number, got type " + type_name(v));
    }
    return out;
}

std::string req_str(const py::dict& d, const char* key) {
    py::object v = req_value(d, key);
    if (!PyUnicode_Check(v.ptr()))
        throw py::type_error(std::string("x13_automatic request field '") + key
                             + "' must be a string, got type " + type_name(v));
    return py::cast<std::string>(v);
}

// Series input: a one-dimensional iterable of real scalars. Text/binary
// containers, pure buffer views (memoryview) and non-scalar elements
// (multivariate rows) are refused; ndarrays (which expose __array__) and
// ordinary iterables stay supported, matching the wrapper's documented
// policy. NaN/Inf elements remain the core's documented policy.
std::vector<double> req_series(const py::dict& d, const char* key) {
    py::object v = req_value(d, key);
    if (is_text(v))
        throw py::type_error(std::string("x13_automatic request field '") + key
                             + "' must be a one-dimensional sequence of numbers; text/binary "
                               "input is refused (a digit string is not a series)");
    if (PyObject_CheckBuffer(v.ptr()) && !PyObject_HasAttrString(v.ptr(), "__array__"))
        throw py::type_error(std::string("x13_automatic request field '") + key
                             + "' must be a one-dimensional sequence of numbers; got the "
                               "buffer-like type " + type_name(v)
                             + " — binary views are refused, 1-D ndarrays are accepted");
    if (PyDict_Check(v.ptr()) || PyAnySet_Check(v.ptr()))
        throw py::type_error(std::string("x13_automatic request field '") + key
                             + "' must be an ordered sequence of numbers, got type "
                             + type_name(v)
                             + " — mapping keys and unordered sets are never a series");
    if (!(PyIter_Check(v.ptr()) || PySequence_Check(v.ptr())))
        throw py::type_error(std::string("x13_automatic request field '") + key
                             + "' must be an iterable of numbers, got the non-iterable type "
                             + type_name(v));
    std::vector<double> out;
    for (py::handle item : py::reinterpret_borrow<py::iterable>(v)) {
        if (is_complex(item)) throw py::type_error("x13_automatic series values must be real");
        if (is_text(item))
            throw py::type_error(std::string("x13_automatic request field '") + key
                                 + "' elements must be real numbers; text elements are refused, "
                                   "not parsed");
        if (PyFloat_Check(item.ptr())) {          // float and np.float64
            out.push_back(PyFloat_AsDouble(item.ptr()));
            continue;
        }
        if (PyIndex_Check(item.ptr())) {
            // NB: EVERY ndarray satisfies PyIndex_Check (numpy fills the slot
            // for all arrays and raises at runtime), so the conversion is the
            // real scalar test: only integer scalars convert.
            PyObject* as_long = PyNumber_Index(item.ptr());
            if (!as_long) {
                PyErr_Clear();
                throw py::type_error(std::string("x13_automatic request field '") + key
                                     + "' has a non-scalar element of type " + type_name(item)
                                     + "; multivariate or mixed input is refused at the "
                                       "boundary");
            }
            double x = PyFloat_AsDouble(as_long);
            Py_DECREF(as_long);
            if (x == -1.0 && PyErr_Occurred()) throw py::error_already_set();
            out.push_back(x);
            continue;
        }
        if (PyObject_HasAttrString(item.ptr(), "__float__") && PyObject_Size(item.ptr()) < 0) {
            PyErr_Clear();  // not sized: numeric scalars like np.float32/Decimal
            double x = PyFloat_AsDouble(item.ptr());
            if (x == -1.0 && PyErr_Occurred()) {
                PyErr_Clear();
                throw py::type_error(std::string("x13_automatic request field '") + key
                                     + "' has a non-numeric element of type "
                                     + type_name(item));
            }
            out.push_back(x);
            continue;
        }
        throw py::type_error(std::string("x13_automatic request field '") + key
                             + "' has a non-scalar or non-numeric element of type "
                             + type_name(item)
                             + "; multivariate or mixed input is refused at the boundary");
    }
    return out;
}

kalos::X13AutomaticRequest build_request(const py::dict& d) {
    using namespace kalos;
    validate_request_keys(d);
    X13AutomaticRequest r;
    r.input = req_series(d, "input");
    r.frequency = req_int<int>(d, "frequency");
    r.first_period = req_int<int>(d, "first_period");
    r.first_year = req_int<int>(d, "first_year");
    r.aicc_log_correction = req_double(d, "aicc_log_correction");
    r.max_d = req_int<int>(d, "max_d");
    r.max_bd = req_int<int>(d, "max_bd");
    r.ub1 = req_double(d, "ub1");
    r.ub2 = req_double(d, "ub2");
    r.cancel = req_double(d, "cancel");
    r.differencing_precision = req_double(d, "differencing_precision");
    r.models_count = req_int<int>(d, "models_count");
    r.max_p = req_int<int>(d, "max_p");
    r.max_q = req_int<int>(d, "max_q");
    r.max_bp = req_int<int>(d, "max_bp");
    r.max_bq = req_int<int>(d, "max_bq");
    r.balanced = req_bool(d, "balanced");
    r.mixed = req_bool(d, "mixed");
    r.arma_accept_white_noise = req_bool(d, "arma_accept_white_noise");
    r.arma_eps = req_double(d, "arma_eps");
    r.outliers_used = req_bool(d, "outliers_used");
    {
        py::object codes = req_value(d, "outlier_types");
        if (is_text(codes) || !(PyIter_Check(codes.ptr()) || PySequence_Check(codes.ptr())))
            throw py::type_error("x13_automatic request field 'outlier_types' must be a "
                                 "sequence of integer codes, got type " + type_name(codes));
        for (py::handle item : py::reinterpret_borrow<py::iterable>(codes)) {
            if (PyBool_Check(item.ptr()) || !PyIndex_Check(item.ptr()))
                throw py::type_error("x13_automatic request field 'outlier_types' codes must "
                                     "be integers (bool and float are refused), got type "
                                     + type_name(item));
            PyObject* as_long = PyNumber_Index(item.ptr());
            if (!as_long) throw py::error_already_set();
            r.outlier_types.push_back(outlier_from_code(py::cast<long>(
                py::reinterpret_steal<py::object>(as_long))));
        }
    }
    {
        if (d.contains("outlier_span")) {
            py::object v = py::reinterpret_borrow<py::object>(d[py::str("outlier_span")]);
            if (!v.is_none()) {
                if (is_text(v))
                    throw py::type_error("x13_automatic request field 'outlier_span' must be "
                                         "None or exactly two integer endpoints, got text");
                if (!(PyIter_Check(v.ptr()) || PySequence_Check(v.ptr())))
                    throw py::type_error("x13_automatic request field 'outlier_span' must be "
                                         "an iterable of two integers, got type " + type_name(v));
                std::vector<py::object> endpoints;
                for (py::handle item : py::reinterpret_borrow<py::iterable>(v))
                    endpoints.push_back(py::reinterpret_borrow<py::object>(item));
                if (endpoints.size() != 2)
                    throw py::type_error("x13_automatic request field 'outlier_span' needs "
                                         "exactly two integer endpoints, got "
                                         + std::to_string(endpoints.size())
                                         + " values; a third endpoint is never silently dropped");
                int ends[2];
                for (std::size_t i = 0; i < 2; ++i) {
                    if (PyBool_Check(endpoints[i].ptr()) || !PyIndex_Check(endpoints[i].ptr()))
                        throw py::type_error("x13_automatic request field 'outlier_span' "
                                             "endpoints must be integers (bool and float are "
                                             "refused), got type " + type_name(endpoints[i]));
                    PyObject* as_long = PyNumber_Index(endpoints[i].ptr());
                    if (!as_long) throw py::error_already_set();
                    ends[i] = py::cast<int>(py::reinterpret_steal<py::object>(as_long));
                }
                r.outlier_span = std::pair<int, int>(ends[0], ends[1]);
            }
        }
    }
    {   // budgets: sign-checked BEFORE the unsigned conversion (REVIEW-1).
        long rounds = req_int<long>(d, "outlier_max_round");
        if (rounds < 0)
            throw py::value_error("x13_automatic request field 'outlier_max_round' must be "
                                  "non-negative, got " + std::to_string(rounds));
        r.outlier_max_round = static_cast<std::size_t>(rounds);
        long cap = req_int<long>(d, "outlier_max_outliers");
        if (cap < 0)
            throw py::value_error("x13_automatic request field 'outlier_max_outliers' must be "
                                  "non-negative, got " + std::to_string(cap));
        r.outlier_max_outliers = static_cast<std::size_t>(cap);
    }
    r.tcrate = req_double(d, "tcrate");
    r.precision = req_double(d, "precision");
    r.mean_precision = req_double(d, "mean_precision");
    r.va = req_double(d, "va");
    r.reduce_va = req_double(d, "reduce_va");
    r.ljung_box_limit = req_double(d, "ljung_box_limit");
    r.check_mu = req_bool(d, "check_mu");
    r.accept_airline = req_bool(d, "accept_airline");
    r.ur_limit = req_double(d, "ur_limit");
    r.mean_test_initial = req_double(d, "mean_test_initial");
    r.mean_test_final = req_double(d, "mean_test_final");
    r.tsig = req_double(d, "tsig");
    r.use_calendar_detection = req_opt_bool(d, "use_calendar_detection", false);
    r.use_easter_detection = req_opt_bool(d, "use_easter_detection", false);
    r.automatic_trading_days = req_opt_bool(d, "automatic_trading_days", false);
    r.use_user_variables = req_opt_bool(d, "use_user_variables", false);
    r.seasonal.clear();
    {
        py::object names = req_value(d, "seasonal");
        if (is_text(names) || !(PyIter_Check(names.ptr()) || PySequence_Check(names.ptr())))
            throw py::type_error("x13_automatic request field 'seasonal' must be a sequence "
                                 "of request names, got type " + type_name(names));
        for (py::handle item : py::reinterpret_borrow<py::iterable>(names)) {
            if (!PyUnicode_Check(item.ptr()))
                throw py::type_error("x13_automatic request field 'seasonal' names must be "
                                     "strings, got type " + type_name(item));
            r.seasonal.push_back(seasonal_from_name(py::cast<std::string>(item)));
        }
    }
    r.trend_length = req_int<int>(d, "trend_length");
    {
        if (d.contains("sigma")) {
            py::object v = py::reinterpret_borrow<py::object>(d[py::str("sigma")]);
            if (!v.is_none()) {
                if (!PyUnicode_Check(v.ptr()))
                    throw py::type_error("x13_automatic request field 'sigma' must be a policy "
                                         "name string or None, got type " + type_name(v));
                std::string pol = py::cast<std::string>(v);
                r.sigma = sigma_from_name(pol);
            }
        }
    }
    r.lower_sigma = req_double(d, "lower_sigma");
    r.upper_sigma = req_double(d, "upper_sigma");
    {
        std::string mp = req_str(d, "msr_policy");
        r.msr_policy = msr_from_name(mp);
    }
    r.mode = mode_from_name(req_str(d, "mode"));
    r.backcast = req_int<int>(d, "backcast");
    r.forecast = req_int<int>(d, "forecast");
    return r;
}

// ---- decision-chain projection ---------------------------------------------

py::object scalars_list(const std::vector<std::pair<std::string, double>>& scalars) {
    py::list out;
    for (const auto& s : scalars) out.append(py::make_tuple(s.first, s.second));
    return out;
}

py::dict transformation_dict(const kalos::TransformationDecisionResult& t) {
    py::dict o;
    o["outcome"] = t.outcome;
    o["log_chosen"] = t.log_chosen;
    o["aicc_level"] = t.aicc_level;
    o["aicc_log"] = t.aicc_log;
    return o;
}

py::dict mean_controller_dict(const kalos::MeanControllerResult& m) {
    py::dict o;
    o["changed"] = m.changed;
    o["mean"] = m.mean;
    o["tstat"] = m.tstat;
    return o;
}

py::dict outlier_scoring_dict(const kalos::OutlierScoringResult& s) {
    py::dict o;
    o["changed"] = s.changed;
    o["stop_reason"] = s.stop_reason;
    o["rounds"] = s.rounds;
    py::list kept;
    for (const auto& d : s.outliers) {
        py::dict e;
        e["position"] = d.position;
        e["type"] = outlier_code(d.type);
        e["t_statistic"] = d.t_statistic;
        e["coefficient"] = d.coefficient;
        kept.append(e);
    }
    o["outliers"] = kept;
    py::list rej;
    for (const auto& r : s.rejections) {
        py::dict e;
        e["position"] = r.position;
        e["type"] = outlier_code(r.type);
        e["abs_t_statistic"] = r.abs_t_statistic;
        e["round"] = r.round;
        e["origin"] = static_cast<int>(r.origin);
        rej.append(e);
    }
    o["rejections"] = rej;
    o["last_scan_max_t"] = s.last_scan_max_t;
    return o;
}

py::dict regtest_dict(const kalos::RegressionVariableTestResult& t) {
    py::dict o;
    o["changed"] = t.changed;
    o["mean"] = t.mean;
    o["preadjustment"] = t.preadjustment;
    o["removed"] = t.removed;
    o["tested"] = t.tested;
    o["accepted"] = t.accepted;
    return o;
}

py::dict accept_dict(const kalos::ModelControllerResult& a) {
    py::dict o;
    o["accepted"] = a.accepted;
    o["rvr"] = a.rvr;
    o["rtval"] = a.rtval;
    o["lb_value"] = a.lb_value;
    o["lb_p"] = a.lb_p;
    o["lb_built"] = a.lb_built;
    return o;
}

py::dict refine_dict(const kalos::ArmaRefinement& f) {
    py::dict o;
    o["p"] = f.p; o["q"] = f.q; o["bp"] = f.bp; o["bq"] = f.bq;
    o["d"] = f.d; o["seasonal_d"] = f.seasonal_d; o["mean"] = f.mean;
    o["specification_changed"] = f.specification_changed;
    o["mean_changed"] = f.mean_changed;
    o["changed"] = f.changed;
    o["fallback"] = f.fallback;
    o["fallback_stage"] = f.fallback_stage;
    if (f.differencing) {
        py::dict dd;
        dd["d"] = f.differencing->d;
        dd["seasonal_d"] = f.differencing->seasonal_d;
        dd["mean_correction"] = f.differencing->mean_correction;
        dd["t_mean"] = f.differencing->t_mean;
        dd["ml_used"] = f.differencing->ml_used;
        dd["nextstep_calls"] = f.differencing->nextstep_calls;
        o["differencing"] = dd;
    } else {
        o["differencing"] = py::none();
    }
    py::list panel;
    for (const auto& m : f.preferred_models) {
        py::dict e;
        e["p"] = m.p; e["q"] = m.q; e["bp"] = m.bp; e["bq"] = m.bq;
        e["bic"] = m.bic;
        panel.append(e);
    }
    o["preferred_models"] = panel;
    o["evaluations_count"] = f.evaluations.size();
    o["refinement_count"] = f.refinement.size();
    return o;
}

py::dict pass2_dict(const kalos::AutoPass2Record& p) {
    py::dict o;
    o["filter"] = p.filter; o["restored"] = p.restored;
    o["continue_round"] = p.continue_round; o["plbox"] = p.plbox;
    o["plbox0"] = p.plbox0; o["rvr"] = p.rvr; o["rtval"] = p.rtval;
    o["pcr_after"] = p.pcr_after; o["loop_after"] = p.loop_after;
    o["curva_after"] = p.curva_after; o["curva_reduced"] = p.curva_reduced;
    o["need_outliers_after"] = p.need_outliers_after;
    o["need_auto_modelling_after"] = p.need_auto_modelling_after;
    o["last_solution"] = p.last_solution;
    return o;
}

py::dict unitroots_dict(const kalos::AutoUnitRootsRecord& u) {
    py::dict o;
    o["regular_count"] = u.regular_count; o["seasonal_count"] = u.seasonal_count;
    o["regular_fired"] = u.regular_fired; o["seasonal_fired"] = u.seasonal_fired;
    o["p_after"] = u.p_after; o["d_after"] = u.d_after;
    o["bp_after"] = u.bp_after; o["bd_after"] = u.bd_after;
    o["regular_margin"] = u.regular_margin; o["seasonal_margin"] = u.seasonal_margin;
    o["redo_estimation"] = u.redo_estimation;
    return o;
}

py::dict matest_dict(const kalos::AutoMaTestRecord& m) {
    py::dict o;
    o["scanned"] = m.scanned; o["abs_theta_at_1"] = m.abs_theta_at_1;
    o["fired"] = m.fired; o["q_after"] = m.q_after; o["d_after"] = m.d_after;
    o["mean_set"] = m.mean_set; o["redo_estimation"] = m.redo_estimation;
    return o;
}

py::dict meanrule_dict(const kalos::AutoMeanRuleRecord& m) {
    py::dict o;
    o["rtval0"] = m.rtval0; o["mean_added"] = m.mean_added;
    return o;
}

py::dict cascade_round_dict(const kalos::AutoCascadeRoundRecord& c) {
    py::dict o;
    o["round"] = c.round; o["estimation_status"] = c.estimation_status;
    o["estimation_ok"] = c.estimation_ok; o["fi_status"] = c.fi_status;
    o["fx"] = c.fx; o["nobs"] = c.nobs;
    o["p_before"] = c.p_before; o["bp_before"] = c.bp_before;
    o["q_before"] = c.q_before; o["bq_before"] = c.bq_before;
    o["p_after"] = c.p_after; o["bp_after"] = c.bp_after;
    o["q_after"] = c.q_after; o["bq_after"] = c.bq_after;
    o["status"] = c.status; o["cascade_ok"] = c.cascade_ok;
    o["asy_diagonal"] = c.asy_diagonal;
    return o;
}

py::dict chain_entry_dict(const kalos::AutoDecisionRecord& e) {
    py::dict o;
    o["stage"] = e.stage;
    o["round"] = e.round;
    o["scalars"] = scalars_list(e.scalars);
    o["notes"] = e.notes;
    auto maybe = [](const auto& payload, auto&& make) -> py::object {
        if (!payload) return py::none();
        return py::object(make(*payload));
    };
    o["transformation"] = maybe(e.transformation, transformation_dict);
    o["mean"] = maybe(e.mean, mean_controller_dict);
    o["outliers"] = maybe(e.outliers, outlier_scoring_dict);
    o["regtest"] = maybe(e.regtest, regtest_dict);
    o["accept"] = maybe(e.accept, accept_dict);
    o["refine"] = maybe(e.refine, refine_dict);
    o["pass2"] = maybe(e.pass2, pass2_dict);
    o["unitroots"] = maybe(e.unitroots, unitroots_dict);
    o["matest"] = maybe(e.matest, matest_dict);
    o["meanrule"] = maybe(e.meanrule, meanrule_dict);
    py::list casc;
    for (const auto& c : e.cascade) casc.append(cascade_round_dict(c));
    o["cascade"] = casc;
    return o;
}

py::dict automatic_result_dict(const kalos::X13AutomaticFitResult& res) {
    using namespace kalos;
    py::dict o;
    o["status"] = res.status;
    o["log"] = res.log; o["mean"] = res.mean;
    o["p"] = res.p; o["q"] = res.q; o["bp"] = res.bp; o["bq"] = res.bq;
    o["d"] = res.d; o["bd"] = res.bd;
    o["coefficients"] = res.coefficients;
    py::list vars;
    for (const auto& v : res.variables) {
        py::dict e;
        e["name"] = v.name;
        e["type"] = outlier_code(v.type);
        e["regeffect"] = v.regeffect;
        e["position"] = v.position;
        e["coefficient"] = v.coefficient;
        vars.append(e);
    }
    o["variables"] = vars;
    o["estimation_status"] = res.estimation_status;
    o["log_likelihood"] = res.log_likelihood;
    o["aicc"] = res.aicc;
    o["effective_observations"] = res.effective_observations;
    py::list chain;
    for (const auto& e : res.chain) chain.append(chain_entry_dict(e));
    o["chain"] = chain;
    // Downstream composition: only the qualified surface the family exposes.
    py::dict fit;
    const X13FitResult& f = res.fit;
    fit["status"] = f.status;
    fit["frequency"] = f.frequency;
    fit["first_period"] = f.first_period;
    fit["log"] = f.log;
    fit["mode_requested"] = mode_name(f.mode_requested);
    fit["mode_effective"] = mode_name(f.mode_effective);
    fit["sigma_set"] = f.sigma_set;
    fit["sigma"] = sigma_name(f.sigma);
    fit["lower_sigma"] = f.lower_sigma;
    fit["upper_sigma"] = f.upper_sigma;
    fit["msr_policy"] = msr_policy_name(f.msr_policy);
    fit["backcast"] = f.backcast;
    fit["forecast"] = f.forecast;
    fit["out"] = f.preadjustment.out;
    fit["preadjustment_status"] = f.preadjustment.status;
    fit["d11final"] = f.finals.d11final;
    fit["e11"] = f.finals.e11;
    fit["finals_status"] = f.finals.status;
    o["fit"] = fit;
    return o;
}

}  // namespace

PYBIND11_MODULE(_kalos, m) {
    m.doc() = "Minimal owned-buffer Kalos bindings";
    bind_preparation(m);
    bind_estimation(m);
    bind_seats(m);
    bind_tramo_preprocessing(m);
    bind_restricted_x13(m);
    m.def("core_version", [] {
        py::dict result;
        result["version"] = kalos::version;
        result["commit"] = kalos::core_revision;
        result["provider"] = kalos::lapack::provider_name();
#ifdef PYKALOS_BUNDLED_OPENBLAS
        result["provider_linkage"] = "private_static";
#else
        result["provider_linkage"] = "external";
#endif
        result["provider_version"] = kalos::lapack::provider_version();
        result["blas_integer_bits"] = 32;
        result["openmp"] = kalos::parallel_info().compiled;
        return result;
    });
    m.def("capabilities", [] {
        py::dict result;
        result["fit"] = false;
        result["primitives"] = py::make_tuple("convolve", "x13_automatic", "x13_fit", "tramo_critical_value",
                                              "tramo_seasonality", "tramo_transform_decision", "tramo_calendar_f_test",
                                              "tramo_full_initial_calendar", "seats_extract_wk", "seats_from_tramo",
                                              "tramoseats_fit", "prepare_regression", "prepare_series", "estimate_sarima_fixed");
        result["status"] = "minimal_binding";
        py::dict restricted;
        restricted["schema_version"] = 1;
        restricted["entry_point"] = "pykalos.x13_fit";
        restricted["qualified"] = true;
        restricted["qualified_frequencies"] = py::make_tuple(4, 12);
        restricted["fixed_coefficients_only"] = true;
        restricted["zero_horizons_only"] = true;
        restricted["fixed_seasonal_filters_only"] = true;
        restricted["fixed_henderson_only"] = true;
        restricted["sigma_policy_default"] = "legacy";
        result["restricted_fit"] = restricted;
        result["tramo_seats_fit"] = py::dict(
            py::arg("entry_point")="pykalos.tramoseats_fit", py::arg("templates")=py::make_tuple("RSA0"),
            py::arg("frequency")=12, py::arg("complete_series_only")=true,
            py::arg("mode")="additive", py::arg("approximation_retry")=true,
            py::arg("approximation_policy")="monthly_airline_legacy",
            py::arg("series_forecast_stdev")=true, py::arg("residuals")=true,
            py::arg("residual_ljung_box")=true, py::arg("residual_doornik_hansen")=true);
        // Schema-3-style automatic block: the qualified stage-Z surface.
        // (3: the 21-H.4 pin advance replaced the zero_horizon_only pin with
        // the horizon envelope key for the downstream composition.)
        py::dict automatic;
        automatic["schema_version"] = 3;
        automatic["x13_automatic_qualified"] = true;
        automatic["sigma_policy_default"] = "legacy";  // maintainer 2026-11-17; applied at the Python wrapper, raw entry stays explicit
        automatic["monthly_only"] = true;
        automatic["frequency"] = 12;
        automatic["horizon_envelope"] = "nonnegative month counts or negative annual counts (12 months per year); combined extended length must fit the core index range (21-H.4)";
        automatic["full_span_outliers_only"] = true;
        automatic["transform_function"] = "auto";
        automatic["modes"] = py::make_tuple("additive", "multiplicative", "log_additive", "pseudo_additive");
        automatic["estimation_solver"] = "pinned_levenberg_marquardt";  // landing and final estimates
        py::dict solvers;
        solvers["landing_and_final"] = automatic["estimation_solver"];
        solvers["differencing_and_initial_arma"] = "pinned_levenberg_marquardt";
        solvers["transform_and_outlier_requests"] = "bfgs";
        automatic["estimation_solver_by_stage"] = solvers;
        automatic["deferred"] = py::make_tuple("calendar", "easter_detection", "automatic_trading_days", "user_variables");
        automatic["refusals"] = "verbatim unsupported:/failed: statuses from the core; never a silent fallback to the restricted fit";
        automatic["entry_points"] = "pykalos.x13_automatic(), _kalos.x13_automatic_fit()";
        result["automatic"] = automatic;
        return result;
    });
    m.def("convolve", [](py::object left_items, py::object right_items) {
        auto left = real_coefficients(left_items);
        auto right = real_coefficients(right_items);
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
    m.def("x13_automatic_fit", [](py::dict spec) {
        // The raw, explicit automatic-spec entry. Every module scalar is
        // required request data here (the core promotes nothing); the sigma
        // policy in particular stays REQUIRED on this path. The family's
        // legacy default and provenance live one layer up in pykalos.py, so
        // this entry never answers "legacy (default)". The request dict is
        // fully read (GIL held) into an owned C++ struct before release; the
        // result graph is owned by the call. No core callback runs on Python.
        kalos::X13AutomaticRequest request = build_request(spec);
        kalos::X13AutomaticFitResult result;
        {
            py::gil_scoped_release release;
            result = kalos::x13_automatic_fit(request);
        }
        return automatic_result_dict(result);
    }, py::arg("request"),
        "Automatic-spec X-13 pipeline (stage Z, item 21-H) on owned buffers.\n"
        "\n"
        "Raw explicit entry: the request dict must carry every decoder-shaped\n"
        "module scalar including a REQUIRED sigma policy; a missing policy\n"
        "answers the pinned core status 'unsupported:x13 fit requires an\n"
        "explicit sigma policy'. Boundary validation (REVIEW-1, all before\n"
        "the core call): keys are checked against the request schema and\n"
        "unknown names raise TypeError (a misspelled optional option is\n"
        "never silently ignored); integer fields must implement __index__\n"
        "(bool/float refused, no truncation); flags must be real Python\n"
        "bools (numpy bool_, ints and text are refused at this raw entry);\n"
        "outlier_span needs exactly two integer endpoints; the two outlier\n"
        "budgets are sign-checked (negative raises ValueError) before the\n"
        "size_t conversion; input is refused as text, binary or\n"
        "multivariate. Scope envelope: frequency 12, horizons\n"
        "in months, or negative counts in years (item 21-H.4),\n"
        "the four decomposition modes, full-span outlier detection, transform\n"
        "function Auto, calendar/easter/TD/user detection deferred (explicit\n"
        "unsupported status). Shape violations raise std::invalid_argument\n"
        "(ValueError in Python). Fail-closed matrix verbatim from the core.\n"
        "Never falls back to the restricted fixed fit.");
}
