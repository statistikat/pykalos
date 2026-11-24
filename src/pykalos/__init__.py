"""Minimal Python interface to the pinned Kalos C++ engine.

Available operations:

* the raw explicit entries re-exported from the extension module
  (``convolve``, ``x13_automatic_fit``) - every core contract stays explicit
  there, nothing is promoted;
* ``x13_automatic`` - the product entry for the automatic-spec X-13
  preprocessing pipeline (item 21-H, stage Z), which applies the family
  product defaults documented on the function. Its boundary input policy
  (which Python/NumPy types each request slot accepts and what is refused,
  never coerced) is documented in the ``x13_automatic`` docstring;
* the fixed-coefficient quarterly/monthly X-13 fit, ``x13_fit``;
* the TRAMO critical value, seasonality and log/level preprocessing decisions;
* fixed WK extraction, fitted TRAMO decomposition and ordinary monthly RSA0, RSA1 and RSA3 fitting.
"""
from . import _kalos
from ._estimation import estimate_sarima_fixed
from ._preparation import prepare_regression, prepare_series
from ._validation import (
    _TEXT_TYPES, _finite_number, _finite_vector, _fixed_integer,
    _request_flag, _request_float, _request_int, _request_series, _request_span,
)
from ._kalos import capabilities, convolve, core_version, x13_automatic_fit

__all__ = ["capabilities", "convolve", "core_version", "x13_automatic",
           "x13_automatic_fit", "x13_fit", "x13_estimated", "tramo_critical_value", "tramo_seasonality",
           "tramo_transform_decision", "tramo_calendar_f_test", "tramo_full_initial_calendar", "tramo_residual_trading_days", "estimate_tramo_tr1", "estimate_tramo_tr3", "estimate_tramo_trfull", "seats_extract_wk", "seats_from_tramo", "tramoseats_fit", "prepare_regression", "prepare_series", "estimate_sarima_fixed"]
__version__ = "0.1.0"

# Decoder-pinned module scalars of the qualified envelope (docs/contracts/
# x13-automatic-pipeline-contract.md on the pinned core; the JVM corpus facts
# under vendor/kalos-evidence echo the same values). The CORE promotes
# nothing: this table is the product wrapper's decoder-equivalent default,
# every entry overridable through x13_automatic(**overrides) and always sent
# explicitly to the raw entry.
_X13_AUTOMATIC_DEFAULTS = {
    "aicc_log_correction": -2.0,     # TransformSpec aicDiff
    "max_d": 2, "max_bd": 1,         # DifferencingModule clamps
    # ub1/ub2 arrive in MODULE space (the decoder hands DifferencingModule
    # the IEEE reciprocal of the spec value; the corpus spec echo is
    # 1.0309278350515465 / 1.1363636363636365 and the reciprocal doubles are
    # what the JVM oracle pinned - the division below IS the pin).
    "ub1": 1.0 / 1.0309278350515465,
    "ub2": 1.0 / 1.1363636363636365,
    "cancel": 0.1,
    "differencing_precision": 1e-7,
    "models_count": 5,               # ArmaModule panel
    "max_p": 2, "max_q": 2, "max_bp": 1, "max_bq": 1,
    "balanced": False, "mixed": True, "arma_accept_white_noise": False,
    "arma_eps": 1e-7,
    "outlier_max_round": 30, "outlier_max_outliers": 30,
    "tcrate": 0.7,                   # monthly transitory-change rate
    "precision": 1e-7,               # kernel-round eps
    "mean_precision": 1e-5,          # MeanController processor eps
    "va": 0.0,                       # 0 -> X13Utility.calcCv(n) rule
    "reduce_va": 0.14286,
    "ljung_box_limit": 0.95,
    "check_mu": True, "accept_airline": False,
    "ur_limit": 0.95,
    "mean_test_initial": 1.96, "mean_test_final": 1.0,  # 0 = no test
    "tsig": 1.0,                     # FinalEstimator cascade ratioLimit
}

_OUTLIER_TYPE_CODES = {"AO": 0, "LS": 1, "TC": 2, "SO": 3}
_MODE_NAMES = ("undefined", "additive", "multiplicative", "log_additive",
               "pseudo_additive")   # the decoder's Undefined == additive request
_SIGMA_POLICIES = ("legacy", "accurate")
_MSR_POLICIES = ("jdplus", "x11_five_year_cap")
_SEASONAL_NAMES = ("stable", "s3x1", "s3x3", "s3x5", "s3x9", "s3x15",
                   "x11default", "msr")


def _fixed_sequence(value, field):
    if isinstance(value, (_TEXT_TYPES, set, frozenset)) or hasattr(value, "keys"):
        raise TypeError(f"x13_fit: {field} must be an ordered sequence")
    try:
        return iter(value)
    except TypeError as exc:
        raise TypeError(f"x13_fit: {field} must be an ordered sequence") from exc


def _fixed_name(value, field):
    if not isinstance(value, str):
        raise TypeError(f"x13_fit: {field} must be a string")
    return value


def x13_fit(series, *, seasonal, trend_length, variables=(), log=False, frequency=12,
            start_period=1, sigma=None, lower_sigma=1.5, upper_sigma=2.5,
            msr_policy="jdplus", mode="additive", backcast=0, forecast=0):
    """Fit a restricted, fixed-coefficient quarterly or monthly X-13 model.

    Supply one seasonal filter name per period and a fixed odd Henderson
    length. Each variable is a mapping with class, effect, a sequence of fixed
    coefficients and one numeric column per coefficient in model order
    (keys: class, effect, coefficient, columns). Each column spans the series.
    sigma defaults to legacy. Horizons must be zero for a completed fixed fit.

    The result echoes the request, effective decomposition mode and core status.
    Available fits include preadjustment, selection decisions, the X-11 tables
    consumed by finals, nine restored tables and finalSA/finalTrend/finalIrregular.
    This route applies supplied coefficients; it performs no parameter estimation.
    """
    fixed_variables = []
    keys = {"class", "effect", "coefficient", "columns"}
    for i, var in enumerate(_fixed_sequence(variables, "variables")):
        if not hasattr(var, "keys") or set(var.keys()) != keys:
            raise ValueError(f"x13_fit: variables[{i}] needs exactly class, effect, coefficient and columns")
        fixed_variables.append({
            "class": _fixed_name(var["class"], "variable class"),
            "effect": _fixed_name(var["effect"], "variable effect"),
            "coefficient": _request_series(var["coefficient"], "coefficient", "x13_fit", allow_boolean=False),
            "columns": [_request_series(col, "column", "x13_fit", allow_boolean=False)
                        for col in _fixed_sequence(var["columns"], "columns")],
        })
    filters = [_fixed_name(value, "seasonal filter") for value in _fixed_sequence(seasonal, "seasonal")]
    policy = "legacy" if sigma is None else _fixed_name(sigma, "sigma")
    out = _kalos._x13_fixed({
        "series": _request_series(series, "series", "x13_fit", allow_boolean=False),
        "variables": fixed_variables, "log": _request_flag(log, "log", "x13_fit"),
        "seasonal": filters, "trend_length": _fixed_integer(trend_length, "trend_length"),
        "frequency": _fixed_integer(frequency, "frequency"),
        "start_period": _fixed_integer(start_period, "start_period"), "sigma": policy,
        "lower_sigma": _request_float(lower_sigma, "lower_sigma", "x13_fit"),
        "upper_sigma": _request_float(upper_sigma, "upper_sigma", "x13_fit"),
        "msr_policy": _fixed_name(msr_policy, "msr_policy"), "mode": _fixed_name(mode, "mode"),
        "backcast": _fixed_integer(backcast, "backcast"), "forecast": _fixed_integer(forecast, "forecast"),
    })
    out["sigma_policy_provenance"] = policy + (" (default)" if sigma is None else " (explicit)")
    return out


def tramo_critical_value(observations):
    """Return TRAMO's critical value for a nonnegative integer observation count."""
    n = _request_int(observations, "observations", "tramo_critical_value")
    if not 0 <= n <= 2**31 - 1:
        raise ValueError("observations must be in the range 0 to 2147483647")
    return _kalos._tramo_critical_value(n)


def _tramo_values(series, frequency, operation):
    if _request_int(frequency, "frequency", operation) != 12:
        raise ValueError(f"{operation} requires monthly data (frequency 12)")
    if getattr(series, "ndim", 1) == 1 and hasattr(series, "__len__") and len(series) > 2**31 - 1:
        raise ValueError(f"{operation}: series exceeds the core index range")
    values = _request_series(series, "series", operation, allow_boolean=False)
    if not 24 <= len(values) <= 2**31 - 1:
        raise ValueError(f"{operation} requires at least 24 monthly observations within the core index range")
    return values


def tramo_seasonality(series, *, frequency=12):
    """Test seasonality in a complete monthly series of at least 24 observations.

    Return the Qs and Friedman tests, seasonality verdict and first-differenced,
    mean-removed data. The first reported difference ends at the second input month.
    """
    return _kalos._tramo_seasonality(_tramo_values(series, frequency, "tramo_seasonality"))


def tramo_calendar_f_test(series, *, start_year, start_month, mean, significance, precision, frequency=12):
    """Fit TRAMO’s monthly working-day and trading-day candidates on the estimation scale.

    Supply complete monthly observations and the first observation's calendar date.
    The result contains the baseline and candidate residual sums of squares, degrees
    of freedom, mean squares, lower-tail probabilities and selected calendar effect.
    """
    operation = "tramo_calendar_f_test"
    arguments = _calendar_domain(series, start_year, start_month, frequency, operation)
    return _kalos._tramo_calendar_f_test(
        *arguments, _request_flag(mean, "mean", operation), _finite_number(significance, "significance", operation),
        _finite_number(precision, "precision", operation))


def _calendar_domain(series, start_year, start_month, frequency, operation):
    if _fixed_integer(frequency, "frequency", operation) != 12:
        raise ValueError(f"{operation} requires monthly data (frequency 12)")
    return (_finite_vector(series, "series", operation), _fixed_integer(start_year, "start_year", operation),
            _fixed_integer(start_month, "start_month", operation))


def tramo_full_initial_calendar(series, *, start_year, start_month, log, frequency=12):
    """Run stock TRfull’s initial calendar module on the original monthly observations.

    The result includes the calendar contrast comparison, t statistics and retention
    decisions for the mean, leap year and Easter. The leap-year t statistic is None
    when the candidate model has no trading-day contrast.
    """
    operation = "tramo_full_initial_calendar"
    arguments = _calendar_domain(series, start_year, start_month, frequency, operation)
    return _kalos._tramo_full_initial_calendar(*arguments, _request_flag(log, "log", operation))


def tramo_residual_trading_days(residuals, *, estimation_start_year, estimation_start_month,
                                estimation_length, significance, frequency=12):
    """Test TRfull's fitted monthly residuals for remaining trading-day variation.

    Dates describe the original estimation window. The residual vector ends on
    its last month and can start later. A rank-deficient or unestimable test returns None.
    """
    operation = "tramo_residual_trading_days"
    arguments = _calendar_domain(residuals, estimation_start_year, estimation_start_month, frequency, operation)
    return _kalos._tramo_residual_trading_days(
        *arguments, _fixed_integer(estimation_length, "estimation_length", operation),
        _finite_number(significance, "significance", operation))


def x13_estimated(series, *, template="RSA0", start_year, start_month, frequency=12):
    """Estimate a stock monthly X-13 model and return fitted components and one year of forecasts.

    RSA0 estimates the additive airline model. RSA1 selects the log/level
    transformation and detects stock outliers. The eight X-11 tables include
    the forecast interval. Final components cover the observation interval.
    """
    if not isinstance(template, str) or template.upper() not in ("RSA0", "RSA1"):
        raise ValueError("x13_estimated supports the monthly RSA0 and RSA1 templates")
    data, year, month = _calendar_domain(series, start_year, start_month, frequency, "x13_estimated")
    if not 1 <= month <= 12:
        raise ValueError("x13_estimated start_month must be between 1 and 12")
    result = _kalos._x13_estimated(data, year, month, template.upper())
    result["template"] = template.upper()
    if result["status"] == "available":
        forecast_year, forecast_position = divmod(12 * year + month - 1 + len(data), 12)
        result["domain"] = dict(start_year=year, start_month=month, length=len(data))
        result["forecast_domain"] = dict(start_year=forecast_year, start_month=forecast_position + 1,
                                         length=len(result["forecast"]["series"]))
    return result


def estimate_tramo_tr1(series, *, start_year, start_month, frequency=12):
    """Fit public TR1 preprocessing to dated, complete monthly observations.

    Returns the chosen transformation, fitted SARIMA model in JVM coefficient
    convention, registered outliers with zero-based observation positions,
    likelihood statistics and dated full residuals.
    """
    operation = "estimate_tramo_tr1"
    return _kalos._estimate_tramo_tr1(*_calendar_domain(series, start_year, start_month, frequency, operation))


def estimate_tramo_tr3(series, *, start_year, start_month, frequency=12):
    """Fit the monthly TR3 automatic SARIMA model and return its dated full residuals."""
    operation = "estimate_tramo_tr3"
    return _kalos._estimate_tramo_tr3(*_calendar_domain(series, start_year, start_month, frequency, operation))


def estimate_tramo_trfull(series, *, start_year, start_month, frequency=12):
    """Fit monthly TRfull with automatic SARIMA, outlier and calendar selection."""
    operation = "estimate_tramo_trfull"
    return _kalos._estimate_tramo_trfull(*_calendar_domain(series, start_year, start_month, frequency, operation))


def tramo_transform_decision(series, log_preference, precision, *, frequency=12, mean=True,
                             detect_seasonality=True, spec_seasonality=True, robust=False):
    """Run the TRAMO monthly log/level decision without robust AO/LS pre-correction.

    Supply a finite log-preference offset and a positive estimation precision.
    The result contains both branch readouts, the chosen transform, chronological
    remarks and a seasonality report (None when detection is disabled).
    """
    op = "tramo_transform_decision"
    if _request_flag(robust, "robust", op):
        raise ValueError(f"{op} requires an input without robust AO/LS pre-correction")
    return _kalos._tramo_transform_decision(
        _tramo_values(series, frequency, op),
        _request_float(log_preference, "log_preference", op),
        _request_float(precision, "precision", op),
        _request_flag(mean, "mean", op),
        _request_flag(detect_seasonality, "detect_seasonality", op),
        _request_flag(spec_seasonality, "spec_seasonality", op),
    )


def x13_automatic(series, *, frequency=12, start_year=1970, start_period=1,
                  mode="undefined", sigma=None, lower_sigma=1.5,
                  upper_sigma=2.5, msr_policy="jdplus", seasonal=None,
                  trend_length=0, outliers=False,
                  outlier_types=("AO", "LS", "TC", "SO"), outlier_span=None,
                  backcast=0, forecast=0,
                  use_calendar_detection=False, use_easter_detection=False,
                  automatic_trading_days=False, use_user_variables=False,
                  **overrides):
    """Run the automatic-spec X-13 preprocessing pipeline (stage Z, item 21-H).

    The pinned RegArimaKernel transcription over the qualified stage-Z units:
    log-level decision, differencing/ARMA auto-modelling, outlier rounds, the
    cascade, then the decoder X-11 composition. Input: a complete finite
    monthly ``series`` (any sequence of numbers) with its calendar position.

    Product defaults applied HERE, at the wrapper layer, never in the core:

    * ``sigma=None`` (omitted) selects the maintainer 2026-11-17 product
      default ``"legacy"`` (bit-exact against the pinned JDemetra
      DefaultExtremeValuesCorrector behaviour); the raw entry
      ``x13_automatic_fit`` keeps the core's explicitness contract and
      answers ``unsupported:x13 fit requires an explicit sigma policy``.
      The result echoes the decision: ``result["sigma_policy"]`` and
      ``result["sigma_policy_provenance"]`` = ``"legacy (default)"`` /
      ``"legacy (explicit)"`` / ``"accurate (explicit)"``.
    * ``_X13_AUTOMATIC_DEFAULTS`` (module scalars, overridable via
      ``**overrides``), the decoder X-11 block (``seasonal=None`` ->
      twelve monthly ``"msr"`` entries, automatic Henderson ``trend_length=0``)
      and the ``"undefined"`` decomposition mode (the decoder's
      X11Spec default).

    Fail-closed, never a silent fallback to a restricted fit: an
    out-of-envelope *specification* (unknown mode/policy/seasonal name, bad
    type) raises ``ValueError``/``TypeError`` before the core call; an
    out-of-envelope *request* answers the contract's verbatim core status in
    ``result["status"]`` ("unsupported:<...>" / "failed:<stage>") with
    ``result["available"] = False`` and the provenance echo intact
    (non-monthly, non-finite input, missing policy on the
    raw entry, deferred calendar/easter/TD/user detection, outlier spans
    narrower than the series, selection-pass refusals). The X-11 horizons
    (``backcast``/``forecast``, month counts; negative meaning |h| annual
    frequencies, normalized by the driver) are IN envelope since item 21-H.4:
    they extend the downstream composition only — estimation, the decision
    chain and the landing coefficients are horizon-invariant. The four forced
    decomposition modes are additive/multiplicative/log_additive/
    pseudo_additive; regression inputs have no surface at all (user-variable
    detection is deferred to 21-I), so nothing outside the delivered scope
    can be requested through this entry.

    Boundary input policy (REVIEW-1; refusals are ``TypeError`` BEFORE the
    core call and nothing is ever truncated or coerced):

    ==========================  ==========================================
    slot                        accepted types
    ==========================  ==========================================
    integer slots               ``int``, integer scalars with ``__index__``
    (``frequency``,             (numpy integer scalars included). ``bool``
    ``start_year``,             refused; EVERY float refused, even an
    ``start_period``,           integral one (``12.9`` and ``12.0`` alike);
    ``backcast``,               text/bytes/``None`` refused.
    ``forecast``,
    ``trend_length``)
    flags (``outliers``,        ``bool``, ``numpy.bool_``. Numbers and text
    ``use_calendar_detection``, refused — the string ``"False"`` would have
    ``use_easter_detection``,   meant ``True`` under truthiness.
    ``automatic_trading_days``,
    ``use_user_variables``)
    ``lower_sigma``/            ``int``/``float`` or a numpy numeric scalar;
    ``upper_sigma``             ``bool``, text and bytes refused.
    ``outlier_span``            ``None`` or EXACTLY two integer-slot values
                                (a third endpoint is an error, never a
                                silent drop; text refused).
    ``series``                  an ordered iterable of real scalars or a
                                1-D ndarray (any dtype float()-able per
                                element). ``str``/``bytes``/bytearray/
                                memoryview, mappings, sets, 0-D and >1-D
                                arrays (multivariate) and text or
                                non-scalar elements refused. NaN/Inf
                                elements stay the core's documented
                                "complete finite series" status.
    ==========================  ==========================================

    Well-formed but unsupported requests (e.g. ``frequency=4``) are NOT
    refused here — they reach the core and keep its documented status
    strings. The default per-month ``seasonal`` allocation happens only
    after the frequency has passed this validation.

    The result is a plain dict: the final description (``log``/``mean``/
    ``p``/``q``/``bp``/``bq``/``d``/``bd``, ``coefficients`` as the four
    Kalos blocks), the selected outlier ``variables``, the landing
    statistics, the full pinned ``chain`` of decision records (stage, round,
    scalars, notes and each machine's projected record), and ``fit`` with
    the downstream composition provenance and the qualified tables (out,
    d11final, e11).
    """
    for name, allowed, values in (("mode", _MODE_NAMES, mode),
                                  ("msr_policy", _MSR_POLICIES, msr_policy)):
        if values not in allowed:
            raise ValueError(f"unknown {name}: {values!r}; expected one of {allowed}")
    if sigma is not None and sigma not in _SIGMA_POLICIES:
        raise ValueError(f"unknown sigma policy: {sigma!r}; expected one of {_SIGMA_POLICIES}")
    unknown = set(overrides) - set(_X13_AUTOMATIC_DEFAULTS)
    if unknown:
        raise TypeError(
            "unexpected x13_automatic specification keys: "
            + ", ".join(sorted(unknown))
            + "; the automatic preprocessing takes no regression inputs "
              "(user-variable detection is deferred to item 21-I)")
    # REVIEW-1: every slot is validated BEFORE any use — the per-month
    # seasonal default is allocated only for the supported monthly route, and
    # no value reaches the request through int()/bool()/float() coercion.
    frequency = _request_int(frequency, "frequency")
    start_year = _request_int(start_year, "start_year")
    start_period = _request_int(start_period, "start_period")
    backcast = _request_int(backcast, "backcast")
    forecast = _request_int(forecast, "forecast")
    trend_length = _request_int(trend_length, "trend_length")
    outliers = _request_flag(outliers, "outliers")
    use_calendar_detection = _request_flag(use_calendar_detection,
                                           "use_calendar_detection")
    use_easter_detection = _request_flag(use_easter_detection,
                                         "use_easter_detection")
    automatic_trading_days = _request_flag(automatic_trading_days,
                                           "automatic_trading_days")
    use_user_variables = _request_flag(use_user_variables, "use_user_variables")
    lower_sigma = _request_float(lower_sigma, "lower_sigma")
    upper_sigma = _request_float(upper_sigma, "upper_sigma")
    outlier_span = _request_span(outlier_span, "outlier_span")
    values = _request_series(series, "series")   # owned copy
    types = sorted({str(t).upper() for t in outlier_types})
    if outliers and not types:
        raise ValueError("outlier detection needs at least one outlier type")
    for t in types:
        if t not in _OUTLIER_TYPE_CODES:
            raise ValueError(f"unknown outlier type: {t!r}; expected one of {sorted(_OUTLIER_TYPE_CODES)}")
    if seasonal is None:
        seasonal = ["msr"] * 12 if frequency == 12 else []
    seasonal = [str(s) for s in seasonal]
    for s in seasonal:
        if s not in _SEASONAL_NAMES:
            raise ValueError(f"unknown seasonal request: {s!r}; expected one of {_SEASONAL_NAMES}")
    policy = "legacy" if sigma is None else sigma  # maintainer 2026-11-17 default
    request = dict(_X13_AUTOMATIC_DEFAULTS)
    request.update(overrides)
    request.update({
        "input": values,
        "frequency": frequency,
        "first_year": start_year,
        "first_period": start_period,
        "outliers_used": outliers,
        "outlier_types": [_OUTLIER_TYPE_CODES[t] for t in types],
        "outlier_span": outlier_span,
        "seasonal": seasonal,
        "trend_length": trend_length,
        "sigma": policy,
        "lower_sigma": lower_sigma,
        "upper_sigma": upper_sigma,
        "msr_policy": msr_policy,
        "mode": mode,
        "backcast": backcast,
        "forecast": forecast,
        "use_calendar_detection": use_calendar_detection,
        "use_easter_detection": use_easter_detection,
        "automatic_trading_days": automatic_trading_days,
        "use_user_variables": use_user_variables,
    })
    result = x13_automatic_fit(request)
    result["sigma_policy"] = policy
    result["sigma_policy_provenance"] = (
        "legacy (default)" if sigma is None else f"{policy} (explicit)")
    result["available"] = result["status"] == "available"
    return result


def _seats_domain(series, spec, operation):
    data = _finite_vector(series, "series", operation)
    for key in ("frequency", "start_year", "start_month", "forecast", "backcast"):
        spec[key] = _fixed_integer(spec[key], key, operation)
    frequency = spec["frequency"]
    if frequency not in (4, 12) or not 1 <= spec["start_month"] <= frequency:
        raise ValueError(f"{operation}: expected frequency 4 or 12 and a start period within the year")
    counts = (spec["backcast"], spec["forecast"])
    extended = len(data) + sum(count if count >= 0 else -frequency * count for count in counts)
    if extended >= 2**31:
        raise ValueError(f"{operation}: SEATS horizons exceed the native index range")
    return data


def _seats_model(series, spec, operation):
    data = _seats_domain(series, spec, operation)
    for key in ("d", "bd"):
        spec[key] = _fixed_integer(spec[key], key, operation)
    if min(spec["d"], spec["bd"]) < 0 or spec["d"] + spec["frequency"] * spec["bd"] >= len(data):
        raise ValueError(f"{operation}: differencing must leave observations")
    for key in ("phi", "bphi", "theta", "btheta"):
        spec[key] = _finite_vector(spec[key], key, operation)
    for key in ("log", "mean_correction"):
        spec[key] = _request_flag(spec[key], key, operation)
    if spec["log"] and any(x <= 0 for x in data):
        raise ValueError(f"{operation}: log transformation requires positive observations")
    return data


def seats_extract_wk(series, innovation_variance, *, frequency=12, start_year=1990, start_month=1,
                     d=0, bd=0, phi=(), theta=(), bphi=(), btheta=(), log=False,
                     mean_correction=True, forecast=-2, backcast=0, approximation="legacy",
                     method="burman", bias="legacy", xl=0.95, epsphi=2.0, rmod=0.5,
                     smod=0.8, smod_pi=0.8):
    """Extract dated initial and final WK rows for a fixed monthly SARIMA model.

    Each row carries component, information, one-based start month, start year,
    and owned values. Negative horizons are in years. The core reports its
    named refusals for unsupported models, estimators and approximation paths.
    """
    spec = locals().copy()
    data = _seats_model(spec.pop("series"), spec, "seats_extract_wk")
    for key in ("innovation_variance", "xl", "epsphi", "rmod", "smod", "smod_pi"):
        spec[key] = _finite_number(spec[key], key, "seats_extract_wk")
    if spec["innovation_variance"] < 0:
        raise ValueError("seats_extract_wk: innovation variance must be nonnegative")
    for key, choices in (("approximation", ("none", "legacy", "noisy")),
                          ("method", ("burman", "kalman_smoother")), ("bias", ("none", "legacy"))):
        if not isinstance(spec[key], str) or spec[key] not in choices:
            raise ValueError(f"seats_extract_wk: {key} must be one of {choices}")
    return _kalos._seats_extract_wk(data, spec)


def seats_from_tramo(series, ssq, effective, estimated, *, frequency=12, start_year=1990,
                     start_month=1, d=0, bd=0, phi=(), theta=(), bphi=(), btheta=(),
                     log=False, mean_correction=True, outliers=(), forecast=-2, backcast=0):
    """Decompose an already fitted monthly TRAMO model and restore its effects.

    Pass the interpolated original-scale observations, fitted residual sum of
    squares, effective observations and number of estimated parameters. Each
    outlier mapping contains type (AO, LS or TC), zero-based observed position
    and coefficient. A TC uses the stock monthly decay of 0.7. The result
    includes initial, final WK and merged rows.
    """
    spec = locals().copy()
    data = _seats_model(spec.pop("series"), spec, "seats_from_tramo")
    spec["ssq"] = _finite_number(ssq, "ssq", "seats_from_tramo")
    for key in ("estimated", "effective"):
        spec[key] = _fixed_integer(spec[key], key, "seats_from_tramo")
    if spec["ssq"] <= 0 or not 0 <= spec["estimated"] < spec["effective"] <= len(data):
        raise ValueError("seats_from_tramo: likelihood requires positive ssq and 0 <= estimated < effective <= length")
    if isinstance(outliers, (_TEXT_TYPES, set, frozenset)) or hasattr(outliers, "keys"):
        raise TypeError("seats_from_tramo: outliers must be an ordered iterable of mappings")
    spec["outliers"] = []
    for row in outliers:
        if not hasattr(row, "keys") or set(row.keys()) != {"type", "position", "coefficient"}:
            raise ValueError("seats_from_tramo: outlier fields must be type, position and coefficient")
        kind = row["type"]
        if not isinstance(kind, str) or kind not in ("AO", "LS", "TC"):
            raise ValueError("seats_from_tramo: outlier type must be AO, LS or TC")
        position = _fixed_integer(row["position"], "position", "seats_from_tramo")
        if not 0 <= position < len(data):
            raise ValueError("seats_from_tramo: outlier position is outside the observations")
        coefficient = _finite_number(row["coefficient"], "coefficient", "seats_from_tramo")
        spec["outliers"].append(dict(type=_OUTLIER_TYPE_CODES[kind], position=position, coefficient=coefficient))
    return _kalos._seats_from_tramo(data, spec)


def tramoseats_fit(series, *, template="RSA0", frequency=12, start_year=1990, start_month=1,
                   forecast=-2, backcast=0):
    """Fit RSA0, RSA1, RSA3 or RSAfull to dated complete monthly observations.

    RSA0 fits the additive airline with a mean. RSA1 chooses the transformation
    and detects outliers. RSA3 also identifies the SARIMA orders. RSAfull selects
    trading days, leap-year and Easter effects. Each returns
    observed finals, dated component rows and fitted preprocessing residuals.
    All four report residual tests and original-series forecast errors.
    Horizon counts are periods when nonnegative and years when negative.
    """
    presets = {"TR0": "RSA0", "RSA0": "RSA0", "TR1": "RSA1", "RSA1": "RSA1", "TR3": "RSA3", "RSA3": "RSA3",
               "TRFULL": "RSAfull", "RSAFULL": "RSAfull"}
    if not isinstance(template, str) or template.upper() not in presets:
        raise ValueError("tramoseats_fit: supported monthly templates are RSA0 (TR0), RSA1 (TR1), RSA3 (TR3) and RSAfull (TRfull)")
    preset = presets[template.upper()]
    spec = dict(frequency=frequency, start_year=start_year, start_month=start_month,
                forecast=forecast, backcast=backcast)
    data = _seats_domain(series, spec, "tramoseats_fit")
    if spec["frequency"] != 12:
        raise ValueError(f"tramoseats_fit: {preset} requires monthly observations")
    # The covariance projection takes months. Domain validation checks these
    # normalized counts against the native integer range before conversion.
    months = [count if count >= 0 else -12 * count for count in (spec["backcast"], spec["forecast"])]
    run = {"RSA0": _kalos._tramoseats_rsa0, "RSA1": _kalos._tramoseats_rsa1, "RSA3": _kalos._tramoseats_rsa3,
           "RSAfull": _kalos._tramoseats_rsafull}[preset]
    result = run(data, spec["start_year"], spec["start_month"], *months)
    first_year, first_period = divmod(12 * spec["start_year"] + spec["start_month"] - 1 + len(data), 12)
    result["series_forecast_domain"] = dict(start_year=first_year, start_month=first_period + 1, length=months[1])
    mode = "multiplicative" if result["model"]["log"] else "additive"
    result.update(template=preset, method="tramoseats", mode=mode, series=data)
    if result["status"] == "ok":
        observed = {row["component"]: row["values"] for row in result["merged"] if row["information"] == "Value"}
        for key, component in (("finalSA", "SeasonallyAdjusted"), ("finalTrend", "Trend"),
                               ("finalSeasonal", "Seasonal"), ("finalIrregular", "Irregular")):
            result[key] = observed[component].copy()
    return result
