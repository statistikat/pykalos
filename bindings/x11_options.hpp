#pragma once
#include <pybind11/pybind11.h>
#include <string>
#include "kalos/x11_selection_pass.hpp"

namespace pykalos_options {
inline const char* mode_name(kalos::X11DecompositionMode m) {
    using M = kalos::X11DecompositionMode;
    switch (m) {
        case M::additive: return "additive";
        case M::multiplicative: return "multiplicative";
        case M::log_additive: return "log_additive";
        case M::pseudo_additive: return "pseudo_additive";
    }
    return "additive";
}

inline const char* sigma_name(kalos::X11SigmaPolicy p) {
    return p == kalos::X11SigmaPolicy::accurate ? "accurate" : "legacy";
}

inline const char* msr_policy_name(kalos::X11MsrIterationPolicy p) {
    return p == kalos::X11MsrIterationPolicy::x11_five_year_cap ? "x11_five_year_cap" : "jdplus";
}

inline const char* seasonal_name(kalos::X11SeasonalRequest r) {
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

inline kalos::X11DecompositionMode mode_from_name(const std::string& s) {
    using M = kalos::X11DecompositionMode;
    if (s == "additive" || s == "undefined") return M::additive;
    if (s == "multiplicative") return M::multiplicative;
    if (s == "log_additive") return M::log_additive;
    if (s == "pseudo_additive") return M::pseudo_additive;
    throw pybind11::value_error("unknown decomposition mode: " + s);
}

inline kalos::X11SeasonalRequest seasonal_from_name(const std::string& s) {
    using R = kalos::X11SeasonalRequest;
    if (s == "stable") return R::stable;
    if (s == "s3x1") return R::s3x1;
    if (s == "s3x3") return R::s3x3;
    if (s == "s3x5") return R::s3x5;
    if (s == "s3x9") return R::s3x9;
    if (s == "s3x15") return R::s3x15;
    if (s == "x11default") return R::x11default;
    if (s == "msr") return R::msr;
    throw pybind11::value_error("unknown seasonal request: " + s);
}

inline kalos::X11SigmaPolicy sigma_from_name(const std::string& value) {
    if (value == "legacy") return kalos::X11SigmaPolicy::legacy;
    if (value == "accurate") return kalos::X11SigmaPolicy::accurate;
    throw pybind11::value_error("unknown sigma policy: " + value);
}

inline kalos::X11MsrIterationPolicy msr_from_name(const std::string& value) {
    if (value == "jdplus") return kalos::X11MsrIterationPolicy::jdplus;
    if (value == "x11_five_year_cap") return kalos::X11MsrIterationPolicy::x11_five_year_cap;
    throw pybind11::value_error("unknown msr policy: " + value);
}
}  // namespace pykalos_options
