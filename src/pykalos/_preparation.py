"""Dated regression-design preparation."""
from . import _kalos
from ._validation import (_TEXT_TYPES, _finite_number, _finite_vector, _fixed_integer, _request_flag,
                          _request_int, _request_series)


def _ordered(value, field, operation):
    if isinstance(value, (_TEXT_TYPES, set, frozenset)) or hasattr(value, "keys"):
        raise TypeError(f"{operation}: {field} must be an ordered iterable")
    try:
        return iter(value)
    except TypeError as exc:
        raise TypeError(f"{operation}: {field} must be an ordered iterable") from exc


def _fields(value, expected, field, operation):
    if not hasattr(value, "keys") or set(value.keys()) != set(expected):
        raise ValueError(f"{operation}: {field} requires exactly the fields {', '.join(expected)}")
    return value


def _date(value, field):
    operation = "prepare_regression"
    year, period = _ordered(value, field, operation)
    year = _request_int(year, field, operation)
    if not -(2**63) <= year < 2**63:
        raise ValueError(f"{operation}: {field} year exceeds the signed 64-bit range")
    return year, _fixed_integer(period, field, operation)


def prepare_regression(length, *, start, frequency, regressors=(), coefficients=(),
                       estimation_start=None, estimation_end=None, d=0, seasonal_d=0,
                       mean=0., include_mean=False, include_drift=False, backcast=0, forecast=0):
    """Align named regression columns to an inclusive monthly or quarterly estimation window.

    Dates are (year, one-based period). Each regressor has name, start and
    values; each supplied coefficient has name, value and a fixed flag. The
    extended columns include the requested nonnegative backcast/forecast
    counts. The observed design contains column vectors, coefficients and
    fixed flags ready to pass to a fixed-order SARIMA estimation request.
    Offsets count observations from zero.
    """
    operation = "prepare_regression"
    inputs, params = [], []
    for row in _ordered(regressors, "regressors", operation):
        _fields(row, ("name", "start", "values"), "regressor", operation)
        if not isinstance(row["name"], str):
            raise TypeError(f"{operation}: regressor name must be a string")
        inputs.append((row["name"], _date(row["start"], "regressor start"),
                       _request_series(row["values"], "regressor values", operation, allow_boolean=False)))
    for row in _ordered(coefficients, "coefficients", operation):
        _fields(row, ("name", "value", "fixed"), "coefficient", operation)
        if not isinstance(row["name"], str):
            raise TypeError(f"{operation}: coefficient name must be a string")
        params.append((row["name"], _finite_number(row["value"], "coefficient", operation),
                       _request_flag(row["fixed"], "fixed", operation)))
    def integer(value, name):
        return _fixed_integer(value, name, operation)
    return _kalos._prepare_regression(
        integer(length, "length"), _date(start, "start"), integer(frequency, "frequency"),
        None if estimation_start is None else _date(estimation_start, "estimation_start"),
        None if estimation_end is None else _date(estimation_end, "estimation_end"),
        inputs, params, integer(d, "d"), integer(seasonal_d, "seasonal_d"),
        _finite_number(mean, "mean", operation), _request_flag(include_mean, "include_mean", operation),
        _request_flag(include_drift, "include_drift", operation), integer(backcast, "backcast"),
        integer(forecast, "forecast"))


def _mask(value, size, field, operation):
    if value is None:
        return [False] * size
    flags = [_request_flag(flag, field, operation) for flag in _ordered(value, field, operation)]
    if len(flags) != size:
        raise ValueError(f"{operation}: {field} must have one entry per value")
    return flags


def prepare_series(series, *, transformation, degree, missing=None, source_offset=0):
    """Transform finite stored values and qualify log-Jacobian rows for a selected window.

    Pass a boolean missing mask and finite placeholders for missing positions.
    Returned local and source row indices are zero-based. Degree is the number
    of leading calendar positions excluded for a logarithmic likelihood.
    """
    operation = "prepare_series"
    if not isinstance(transformation, str) or transformation not in ("none", "log"):
        raise ValueError("prepare_series: transformation must be none or log")
    data = _finite_vector(series, "series", operation)
    mask = _mask(missing, len(data), "missing", operation)
    degree = _fixed_integer(degree, "degree", operation)
    source_offset = _request_int(source_offset, "source_offset", operation)
    if degree < 0 or not 0 <= source_offset < 2**63:
        raise ValueError("prepare_series: degree and source_offset must be nonnegative and within range")
    result = _kalos._prepare_series(data, mask, transformation == "log", degree, source_offset)
    result["missing"] = mask
    return result
