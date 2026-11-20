"""Minimal Python interface to the pinned Kalos C++ engine.

Two surfaces:

* the raw explicit entries re-exported from the extension module
  (``convolve``, ``x13_automatic_fit``) - every core contract stays explicit
  there, nothing is promoted;
* ``x13_automatic`` - the product entry for the automatic-spec X-13
  preprocessing pipeline (item 21-H, stage Z), which applies the family
  product defaults documented on the function.
"""
from ._kalos import capabilities, convolve, core_version, x13_automatic_fit

__all__ = ["capabilities", "convolve", "core_version", "x13_automatic",
           "x13_automatic_fit"]
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
      ``["msr"] * frequency``, automatic Henderson ``trend_length=0``)
      and the ``"undefined"`` decomposition mode (the decoder's
      X11Spec default).

    Fail-closed, never a silent fallback to a restricted fit: an
    out-of-envelope *specification* (unknown mode/policy/seasonal name, bad
    type) raises ``ValueError``/``TypeError`` before the core call; an
    out-of-envelope *request* answers the contract's verbatim core status in
    ``result["status"]`` ("unsupported:<...>" / "failed:<stage>") with
    ``result["available"] = False`` and the provenance echo intact
    (non-monthly, non-finite input, nonzero horizons, missing policy on the
    raw entry, deferred calendar/easter/TD/user detection, outlier spans
    narrower than the series, selection-pass refusals). The four forced
    decomposition modes are additive/multiplicative/log_additive/
    pseudo_additive; regression inputs have no surface at all (user-variable
    detection is deferred to 21-I), so nothing outside the delivered scope
    can be requested through this entry.

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
    if seasonal is None:
        seasonal = ["msr"] * int(frequency)
    seasonal = [str(s) for s in seasonal]
    for s in seasonal:
        if s not in _SEASONAL_NAMES:
            raise ValueError(f"unknown seasonal request: {s!r}; expected one of {_SEASONAL_NAMES}")
    types = sorted({str(t).upper() for t in outlier_types})
    if outliers and not types:
        raise ValueError("outlier detection needs at least one outlier type")
    for t in types:
        if t not in _OUTLIER_TYPE_CODES:
            raise ValueError(f"unknown outlier type: {t!r}; expected one of {sorted(_OUTLIER_TYPE_CODES)}")
    values = [float(v) for v in series]   # owned copy; non-numeric raises TypeError
    policy = "legacy" if sigma is None else sigma  # maintainer 2026-11-17 default
    request = dict(_X13_AUTOMATIC_DEFAULTS)
    request.update(overrides)
    request.update({
        "input": values,
        "frequency": int(frequency),
        "first_year": int(start_year),
        "first_period": int(start_period),
        "outliers_used": bool(outliers),
        "outlier_types": [_OUTLIER_TYPE_CODES[t] for t in types],
        "outlier_span": None if outlier_span is None else (int(outlier_span[0]), int(outlier_span[1])),
        "seasonal": seasonal,
        "trend_length": int(trend_length),
        "sigma": policy,
        "lower_sigma": float(lower_sigma),
        "upper_sigma": float(upper_sigma),
        "msr_policy": msr_policy,
        "mode": mode,
        "backcast": int(backcast),
        "forecast": int(forecast),
        "use_calendar_detection": bool(use_calendar_detection),
        "use_easter_detection": bool(use_easter_detection),
        "automatic_trading_days": bool(automatic_trading_days),
        "use_user_variables": bool(use_user_variables),
    })
    result = x13_automatic_fit(request)
    result["sigma_policy"] = policy
    result["sigma_policy_provenance"] = (
        "legacy (default)" if sigma is None else f"{policy} (explicit)")
    result["available"] = result["status"] == "available"
    return result
