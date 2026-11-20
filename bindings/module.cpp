#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <cstdint>
#include <optional>
#include <string>
#include <vector>
#include "kalos/numerics.hpp"
#include "kalos/version.hpp"
#include "kalos/parallel.hpp"
#include "kalos/detail/lapack.hpp"
#include "kalos/x13_automatic.hpp"
namespace py = pybind11;

namespace {

// ---- enum name mirrors (boundary vocabulary; never re-decided in Python) ----

const char* mode_name(kalos::X11DecompositionMode m) {
    using M = kalos::X11DecompositionMode;
    switch (m) {
        case M::additive: return "additive";
        case M::multiplicative: return "multiplicative";
        case M::log_additive: return "log_additive";
        case M::pseudo_additive: return "pseudo_additive";
    }
    return "additive";
}

const char* sigma_name(kalos::X11SigmaPolicy p) {
    return p == kalos::X11SigmaPolicy::accurate ? "accurate" : "legacy";
}

const char* msr_policy_name(kalos::X11MsrIterationPolicy p) {
    return p == kalos::X11MsrIterationPolicy::x11_five_year_cap ? "x11_five_year_cap" : "jdplus";
}

const char* seasonal_name(kalos::X11SeasonalRequest r) {
    switch (r) {
        case kalos::X11SeasonalRequest::stable: return "stable";
        case kalos::X11SeasonalRequest::s3x1: return "s3x1";
        case kalos::X11SeasonalRequest::s3x3: return "s3x3";
        case kalos::X11SeasonalRequest::s3x5: return "s3x5";
        case kalos::X11SeasonalRequest::s3x9: return "s3x9";
        case kalos::X11SeasonalRequest::s3x15: return "s3x15";
        case kalos::X11SeasonalRequest::x11default: return "x11default";
        case kalos::X11SeasonalRequest::msr: return "msr";
    }
    return "stable";
}

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

template <typename T>
T req_field(const py::dict& d, const char* key) {
    if (!d.contains(key)) throw py::key_error(std::string("x13_automatic request missing field: ") + key);
    return py::cast<T>(d[py::str(key)]);
}

bool req_opt_bool(const py::dict& d, const char* key, bool fallback) {
    if (!d.contains(key) || d[py::str(key)].is_none()) return fallback;
    return py::cast<bool>(d[py::str(key)]);
}

kalos::X11DecompositionMode mode_from_name(const std::string& s) {
    using M = kalos::X11DecompositionMode;
    if (s == "additive" || s == "undefined") return M::additive;
    if (s == "multiplicative") return M::multiplicative;
    if (s == "log_additive") return M::log_additive;
    if (s == "pseudo_additive") return M::pseudo_additive;
    throw py::value_error("unknown decomposition mode: " + s);
}

kalos::X11SeasonalRequest seasonal_from_name(const std::string& s) {
    using R = kalos::X11SeasonalRequest;
    if (s == "stable") return R::stable;
    if (s == "s3x1") return R::s3x1;
    if (s == "s3x3") return R::s3x3;
    if (s == "s3x5") return R::s3x5;
    if (s == "s3x9") return R::s3x9;
    if (s == "s3x15") return R::s3x15;
    if (s == "x11default") return R::x11default;
    if (s == "msr") return R::msr;
    throw py::value_error("unknown seasonal request: " + s);
}

kalos::X13AutomaticRequest build_request(const py::dict& d) {
    using namespace kalos;
    X13AutomaticRequest r;
    r.input = req_field<std::vector<double>>(d, "input");
    r.frequency = req_field<int>(d, "frequency");
    r.first_period = req_field<int>(d, "first_period");
    r.first_year = req_field<int>(d, "first_year");
    r.aicc_log_correction = req_field<double>(d, "aicc_log_correction");
    r.max_d = req_field<int>(d, "max_d");
    r.max_bd = req_field<int>(d, "max_bd");
    r.ub1 = req_field<double>(d, "ub1");
    r.ub2 = req_field<double>(d, "ub2");
    r.cancel = req_field<double>(d, "cancel");
    r.differencing_precision = req_field<double>(d, "differencing_precision");
    r.models_count = req_field<int>(d, "models_count");
    r.max_p = req_field<int>(d, "max_p");
    r.max_q = req_field<int>(d, "max_q");
    r.max_bp = req_field<int>(d, "max_bp");
    r.max_bq = req_field<int>(d, "max_bq");
    r.balanced = req_field<bool>(d, "balanced");
    r.mixed = req_field<bool>(d, "mixed");
    r.arma_accept_white_noise = req_field<bool>(d, "arma_accept_white_noise");
    r.arma_eps = req_field<double>(d, "arma_eps");
    r.outliers_used = req_field<bool>(d, "outliers_used");
    for (long code : req_field<std::vector<long>>(d, "outlier_types"))
        r.outlier_types.push_back(outlier_from_code(code));
    if (d.contains(py::str("outlier_span")) && !d[py::str("outlier_span")].is_none()) {
        auto span = py::cast<std::pair<int, int>>(d[py::str("outlier_span")]);
        r.outlier_span = span;
    }
    r.outlier_max_round = static_cast<std::size_t>(req_field<long>(d, "outlier_max_round"));
    r.outlier_max_outliers = static_cast<std::size_t>(req_field<long>(d, "outlier_max_outliers"));
    r.tcrate = req_field<double>(d, "tcrate");
    r.precision = req_field<double>(d, "precision");
    r.mean_precision = req_field<double>(d, "mean_precision");
    r.va = req_field<double>(d, "va");
    r.reduce_va = req_field<double>(d, "reduce_va");
    r.ljung_box_limit = req_field<double>(d, "ljung_box_limit");
    r.check_mu = req_field<bool>(d, "check_mu");
    r.accept_airline = req_field<bool>(d, "accept_airline");
    r.ur_limit = req_field<double>(d, "ur_limit");
    r.mean_test_initial = req_field<double>(d, "mean_test_initial");
    r.mean_test_final = req_field<double>(d, "mean_test_final");
    r.tsig = req_field<double>(d, "tsig");
    r.use_calendar_detection = req_opt_bool(d, "use_calendar_detection", false);
    r.use_easter_detection = req_opt_bool(d, "use_easter_detection", false);
    r.automatic_trading_days = req_opt_bool(d, "automatic_trading_days", false);
    r.use_user_variables = req_opt_bool(d, "use_user_variables", false);
    r.seasonal.clear();
    for (const std::string& s : req_field<std::vector<std::string>>(d, "seasonal"))
        r.seasonal.push_back(seasonal_from_name(s));
    r.trend_length = req_field<int>(d, "trend_length");
    if (d.contains(py::str("sigma")) && !d[py::str("sigma")].is_none()) {
        std::string pol = py::cast<std::string>(d[py::str("sigma")]);
        if (pol == "legacy") r.sigma = X11SigmaPolicy::legacy;
        else if (pol == "accurate") r.sigma = X11SigmaPolicy::accurate;
        else throw py::value_error("unknown sigma policy: " + pol);
    }
    r.lower_sigma = req_field<double>(d, "lower_sigma");
    r.upper_sigma = req_field<double>(d, "upper_sigma");
    {
        std::string mp = req_field<std::string>(d, "msr_policy");
        if (mp == "jdplus") r.msr_policy = X11MsrIterationPolicy::jdplus;
        else if (mp == "x11_five_year_cap") r.msr_policy = X11MsrIterationPolicy::x11_five_year_cap;
        else throw py::value_error("unknown msr policy: " + mp);
    }
    r.mode = mode_from_name(req_field<std::string>(d, "mode"));
    r.backcast = req_field<int>(d, "backcast");
    r.forecast = req_field<int>(d, "forecast");
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
        result["primitives"] = py::make_tuple("convolve", "x13_automatic");
        result["status"] = "minimal_binding";
        // Schema-3-style automatic block: the qualified stage-Z surface.
        // (3: the 21-H.4 pin advance replaced the zero_horizon_only pin with
        // the horizon envelope key — horizons are month counts >= 0 in the
        // product envelope and extend the downstream composition only.)
        py::dict automatic;
        automatic["schema_version"] = 3;
        automatic["x13_automatic_qualified"] = true;
        automatic["sigma_policy_default"] = "legacy";  // maintainer 2026-11-17; applied at the Python wrapper, raw entry stays explicit
        automatic["monthly_only"] = true;
        automatic["frequency"] = 12;
        automatic["horizon_envelope"] = "backcast/forecast month counts >= 0 (item 21-H.4 initialStep route; downstream composition only)";
        automatic["full_span_outliers_only"] = true;
        automatic["transform_function"] = "auto";
        automatic["modes"] = py::make_tuple("additive", "multiplicative", "log_additive", "pseudo_additive");
        automatic["estimation_solver"] = "bfgs_default";
        automatic["deferred"] = py::make_tuple("calendar", "easter_detection", "automatic_trading_days", "user_variables");
        automatic["refusals"] = "verbatim unsupported:/failed: statuses from the core; never a silent fallback to the restricted fit";
        automatic["entry_points"] = "pykalos.x13_automatic(), _kalos.x13_automatic_fit()";
        result["automatic"] = automatic;
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
        "explicit sigma policy'. Scope envelope: frequency 12, horizons\n"
        "{0..N} month counts (item 21-H.4),\n"
        "the four decomposition modes, full-span outlier detection, transform\n"
        "function Auto, calendar/easter/TD/user detection deferred (explicit\n"
        "unsupported status). Shape violations raise std::invalid_argument\n"
        "(ValueError in Python). Fail-closed matrix verbatim from the core.\n"
        "Never falls back to the restricted fixed fit.");
}
