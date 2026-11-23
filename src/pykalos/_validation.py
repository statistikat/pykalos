"""Shared scalar and series validation at the Python boundary."""
from math import isfinite as _isfinite
from operator import index as _index


# ---- boundary validation (REVIEW-1: refuse malformed, never coerce) ----------
#
# Policy table (also documented on x13_automatic):
#   integer slots (frequency, start_year, start_period, backcast, forecast,
#     trend_length): Python int or an integer scalar implementing
#     __index__ (numpy integer scalars included). bool is REFUSED, every
#     float is REFUSED (even an integral one like 12.0), text/bytes/None are
#     REFUSED. Nothing is ever truncated: 12.9 never becomes 12, 0.9 never
#     becomes 0.
#   flags (outliers and the four deferred-detection flags): bool or
#     numpy.bool_ only. Numbers (1, 0) and text ("False") are REFUSED —
#     truthiness is never a decision input.
#   real slots (lower_sigma, upper_sigma): int/float or a numpy numeric
#     scalar (anything float()-able); bool, text and bytes are REFUSED.
#   outlier_span: None, or exactly two integer-slot endpoints. A third
#     value is an error, never a silent drop; text is REFUSED.
#   series: an ordered iterable of real scalars or a one-dimensional
#     ndarray. str/bytes/bytearray/memoryview, mappings, sets, 0-D and
#     >1-D arrays (multivariate) and non-scalar or text elements are
#     REFUSED at the boundary. NaN/Inf elements stay the core's policy
#     (documented "complete finite series" status), matching the M2
#     convolve-boundary doctrine.
# Well-formed-but-unsupported requests (e.g. frequency=4) are NOT refused
# here: they reach the core and keep its documented status strings.

_TEXT_TYPES = (str, bytes, bytearray, memoryview)


def _type_name(value):
    return type(value).__name__


def _is_numpy_bool(value):
    # duck-typed so the package never imports numpy: a numpy bool scalar is
    # exactly a scalar whose type lives in the numpy module and is named
    # bool_ (numpy 1) or bool (numpy 2 renamed the public scalar type).
    return type(value).__module__ == "numpy" and type(value).__name__ in ("bool", "bool_")


def _request_int(value, name, operation="x13_automatic"):
    """Exact integer or refuse: no truncation, no bool, no integral float."""
    if isinstance(value, bool) or _is_numpy_bool(value):
        raise TypeError(
            f"{operation}: {name} must be an integer, got the boolean "
            f"{value!r}; booleans are never accepted as numbers")
    if hasattr(value, "__index__"):   # Python int, numpy integer scalars, ...
        return _index(value)
    if isinstance(value, float):
        raise TypeError(
            f"{operation}: {name} must be an integer, got the float "
            f"{value!r}; fractional values are refused (no truncation) and "
            f"integral floats are not accepted either — pass the integer "
            f"int({value}) if it is what you meant")
    raise TypeError(
        f"{operation}: {name} must be an integer, got {value!r} "
        f"of type {_type_name(value)}; text and None are refused")


def _request_flag(value, name, operation="x13_automatic"):
    """Real bool or numpy bool_ only: 'False'/'1'/1 must not mean anything."""
    if isinstance(value, bool):
        return value
    if _is_numpy_bool(value):
        return bool(value)
    raise TypeError(
        f"{operation}: {name} must be True or False (a bool, or a numpy "
        f"bool_), got {value!r} of type {_type_name(value)}; truthiness is "
        f"never a decision input — the string 'False' would have meant True")


def _is_complex(value):
    return isinstance(value, complex) or getattr(getattr(value, "dtype", None), "kind", None) == "c"


def _request_float(value, name, operation="x13_automatic"):
    """Real scalar number for a float slot: no bool, no text, no containers."""
    if isinstance(value, bool) or _is_numpy_bool(value):
        raise TypeError(
            f"{operation}: {name} must be a real number, got the boolean "
            f"{value!r}; booleans are never accepted as numbers")
    if _is_complex(value):
        raise TypeError(f"{operation}: {name} must be real; complex values are refused")
    if isinstance(value, _TEXT_TYPES):
        raise TypeError(
            f"{operation}: {name} must be a real number, got "
            f"{value!r} of type {_type_name(value)}; text is refused")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(
            f"{operation}: {name} must be a real number, got {value!r} "
            f"of type {_type_name(value)}") from exc


def _request_span(value, name):
    """None or exactly two integer endpoints; the third value is an error."""
    if value is None:
        return None
    if isinstance(value, _TEXT_TYPES):
        raise TypeError(
            f"x13_automatic: {name} must be None or exactly two integer "
            f"endpoints, got the text value {value!r}; a string of digits "
            f"is not a span")
    try:
        endpoints = list(value)
    except TypeError as exc:
        raise TypeError(
            f"x13_automatic: {name} must be None or exactly two integer "
            f"endpoints, got the non-iterable {value!r}") from exc
    if len(endpoints) != 2:
        raise TypeError(
            f"x13_automatic: {name} needs exactly two integer endpoints, "
            f"got {len(endpoints)} values: {value!r}; a third endpoint is "
            f"never silently dropped")
    return (_request_int(endpoints[0], f"{name}[0]"),
            _request_int(endpoints[1], f"{name}[1]"))


def _request_series(values, name, operation="x13_automatic", *, allow_boolean=True):
    """Owned list of floats, or an explicit refusal; never text/binary/matrix."""
    if isinstance(values, _TEXT_TYPES):
        raise TypeError(
            f"{operation}: {name} must be a one-dimensional sequence of "
            f"numbers, got {_type_name(values)}; text/binary input is "
            f"refused (a digit string is not a series)")
    if isinstance(values, dict) or hasattr(values, "keys"):
        raise TypeError(
            f"{operation}: {name} must be a one-dimensional sequence of "
            f"numbers, got a mapping; iterating a mapping's keys is never "
            f"a series")
    if isinstance(values, (set, frozenset)):
        raise TypeError(
            f"{operation}: {name} must be an ordered sequence, got a "
            f"set; sets carry no calendar order")
    ndim = getattr(values, "ndim", None)
    if ndim is not None:
        if ndim == 0:
            raise TypeError(
                f"{operation}: {name} must be a one-dimensional sequence "
                f"of numbers, got the 0-D scalar value {values!r}")
        if ndim != 1:
            raise TypeError(
                f"{operation}: {name} must be a one-dimensional sequence "
                f"of numbers, got an array with ndim={ndim}; multivariate "
                f"input is refused")
    try:
        items = list(values)
    except TypeError as exc:
        raise TypeError(
            f"{operation}: {name} must be an iterable of numbers or a "
            f"1-D array, got the non-iterable {_type_name(values)}") from exc
    out = []
    for i, v in enumerate(items):
        if _is_complex(v):
            raise TypeError(f"{operation}: {name} element {i} must be real; complex values are refused")
        if not allow_boolean and (isinstance(v, bool) or _is_numpy_bool(v)):
            raise TypeError(f"{operation}: {name} element {i} must be numeric, got a boolean")
        if isinstance(v, _TEXT_TYPES):
            raise TypeError(
                f"{operation}: {name} element {i} is text/binary "
                f"({v!r}); text elements are refused, not parsed")
        if hasattr(v, "__iter__") or getattr(v, "ndim", 0):
            raise TypeError(
                f"{operation}: {name} element {i} is not a scalar; "
                f"multivariate input is refused at the boundary")
        try:
            out.append(float(v))
        except (TypeError, ValueError) as exc:
            raise TypeError(
                f"{operation}: {name} element {i} is not numeric: "
                f"{v!r} of type {_type_name(v)}") from exc
    return out


def _fixed_integer(value, field, operation="x13_fit"):
    value = _request_int(value, field, operation)
    if not -2**31 <= value < 2**31:
        raise ValueError(f"{operation}: {field} is outside the supported integer range")
    return value


def _finite_number(value, field, operation):
    if getattr(value, "ndim", 0):
        raise TypeError(f"{operation}: {field} must be a finite real scalar")
    value = _request_float(value, field, operation)
    if not _isfinite(value):
        raise ValueError(f"{operation}: {field} must be finite")
    return value


def _finite_vector(values, field, operation):
    if hasattr(values, "__len__") and len(values) >= 2**31:
        raise ValueError(f"{operation}: {field} exceeds the native index range")
    result = _request_series(values, field, operation, allow_boolean=False)
    if not all(_isfinite(value) for value in result):
        raise ValueError(f"{operation}: {field} must contain only finite values")
    return result
