"""Fixed-order SARIMA estimation control."""
from . import _kalos
from ._preparation import _fields, _mask, _ordered
from ._validation import _finite_number, _finite_vector, _fixed_integer, _request_flag


OPERATION = "estimate_sarima_fixed"
BLOCKS = ("ar", "ma", "seasonal_ar", "seasonal_ma")


def _options(value, names, field):
    if not hasattr(value, "keys") or set(value.keys()).difference(names):
        raise ValueError(f"{OPERATION}: unknown {field} fields; allowed fields are {', '.join(names)}")
    return dict(value)


def _design(value, n):
    if value is None:
        return dict(columns=[], coefficients=[], fixed=[])
    _fields(value, ("columns", "coefficients", "fixed"), "design", OPERATION)
    columns = [_finite_vector(column, "design column", OPERATION)
               for column in _ordered(value["columns"], "columns", OPERATION)]
    if any(len(column) != n for column in columns):
        raise ValueError(f"{OPERATION}: each design column must match the response length")
    coefficients = _finite_vector(value["coefficients"], "design coefficients", OPERATION)
    if len(coefficients) != len(columns):
        raise ValueError(f"{OPERATION}: one regression coefficient is required per column")
    return dict(columns=columns, coefficients=coefficients,
                fixed=_mask(value["fixed"], len(columns), "design fixed flags", OPERATION, optional=False))


def _blocks(value):
    supplied = _options(value, BLOCKS, "coefficient block")
    output = {}
    for name in BLOCKS:
        block = supplied.get(name, dict(initial=[], fixed=[]))
        _fields(block, ("initial","fixed"), name, OPERATION)
        initial = _finite_vector(block["initial"], name, OPERATION)
        fixed = _mask(block["fixed"], len(initial), name + " fixed flags", OPERATION, optional=False)
        output[name] = dict(initial=initial, fixed=fixed)
    return output


def _control(value):
    flags = ("maximum_likelihood", "unit_root_search", "corrected_degrees_of_freedom", "fast_derivatives")
    _fields(value, ("eps", "feps", "starting_point", "solver", *flags), "control", OPERATION)
    output = {key: _request_flag(value[key], key, OPERATION) for key in flags}
    for key in ("eps","feps"):
        output[key] = _finite_number(value[key], key, OPERATION)
    for key, choices in (("starting_point", ("zero", "default", "hannan_rissanen", "multiple")),
                         ("solver", ("bfgs", "pinned_levenberg_marquardt"))):
        if not isinstance(value[key], str) or value[key] not in choices:
            raise ValueError(f"{OPERATION}: {key} must be one of {choices}")
        output[key] = value[key]
    return output


def _optimizer(value):
    if value is None:
        return {}
    integers = ("max_iterations","max_evaluations","max_line_search","difference_refinements")
    numbers = ("gradient_tolerance","step_tolerance","function_tolerance","difference_step","armijo","max_step")
    output = _options(value, (*integers, *numbers), "optimizer")
    for key in output:
        validate = _fixed_integer if key in integers else _finite_number
        output[key] = validate(output[key], key, OPERATION)
    return output


def estimate_sarima_fixed(series, *, period, d, seasonal_d, blocks, control, design=None, missing=None,
                          optimizer=None, spec_d=None, spec_seasonal_d=None, request_landing_point=False):
    """Estimate a specified SARIMA structure using the explicit pinned estimation control.

    Blocks are ar, ma, seasonal_ar and seasonal_ma. Each supplied block has
    initial values and boolean fixed flags. Omitted blocks have order zero.
    Coefficients use Kalos signs (AR polynomial 1−phi B, MA 1+theta B).
    Pass a prepared observed regression design or omit it for no regression.
    Missing positions use finite stored placeholders and a boolean mask.
    The result carries the retained coefficients, likelihood and chronological
    decisions of each estimation pass. The control keys are documented in the README.
    """
    data = _finite_vector(series, "series", OPERATION)
    request = dict(series=data, missing=_mask(missing, len(data), "missing", OPERATION),
                   blocks=_blocks(blocks), control=_control(control), design=_design(design, len(data)),
                   optimizer=_optimizer(optimizer), request_landing_point=_request_flag(
                       request_landing_point, "request_landing_point", OPERATION))
    for key, val in (("d", d), ("period", period), ("seasonal_d", seasonal_d),
                     ("spec_d", -1 if spec_d is None else spec_d),
                     ("spec_seasonal_d", -1 if spec_seasonal_d is None else spec_seasonal_d)):
        request[key] = _fixed_integer(val, key, OPERATION)
    return _kalos._estimate_sarima_fixed(request)
