"""REVIEW-1: request-validation hardening at the Python and raw-bindings boundary.

Pins the two P1 sections of adaption_in_the_implemetation_needed.md
(external review, 2026-11-23, at 808e01c):

* "Validate the Python automatic-fit request before coercion" — every
  malformed input from the review's probe list must raise at the boundary
  with a naming error instead of being coerced (12.9 never becomes 12,
  0.9 never becomes 0, the third span value is never dropped, the string
  "False" never means True, digit strings/bytes/multivariate never reach
  the core as series input).
* "Reject unknown raw keys and negative budgets" — a misspelled optional
  key (use_calender_detection) must raise naming it, and the two outlier
  budgets must be sign-checked before the size_t conversion.

It ALSO pins the other half of the doctrine: valid-but-unsupported
requests (quarterly frequency, NaN series, deferred flags, narrow outlier
spans) keep the core's verbatim status responses — the boundary only
refuses malformed input — and valid monthly/quarterly rows and the
accepted numpy interop set (integer scalars, bool_ flags on the product
entry) are unchanged.
"""
import importlib.util
import unittest

import pykalos
from x13auto_corpus import load_corpus

HAS_NUMPY = importlib.util.find_spec("numpy") is not None
if HAS_NUMPY:
    import numpy as np

CORPUS = load_corpus()
QUICK = CORPUS["quick"]

MONTHLY_ONLY = "unsupported:x13 automatic fit monthly series only"
DEFERRED = ("unsupported:x13 automatic fit defers calendar/easter/TD/"
            "user detection (21-I)")
SPAN_ONLY = "unsupported:x13 automatic fit spans the full series only"
FINITE = "unsupported:x13 automatic fit requires a complete finite series"


def quick_request(**kw):
    """Product-entry call on the pinned quick case (short, fully qualified)."""
    kw.setdefault("start_year", QUICK["first_year"])
    kw.setdefault("start_period", QUICK["first_period"])
    return pykalos.x13_automatic(QUICK["values"], **kw)


class IntegerSlotTest(unittest.TestCase):
    """Scalar integer fields: exact values only; the reviewer's probe trio."""

    def test_fractional_frequency_refused(self):
        with self.assertRaises(TypeError) as ctx:
            quick_request(frequency=12.9, seasonal=["msr"] * 12)
        self.assertIn("frequency", str(ctx.exception))
        self.assertIn("12.9", str(ctx.exception))

    def test_fractional_start_period_refused(self):
        with self.assertRaises(TypeError) as ctx:
            quick_request(start_period=1.9)
        self.assertIn("start_period", str(ctx.exception))

    def test_fractional_forecast_refused_not_zeroed(self):
        # 0.9 -> 0 silently REMOVED the requested horizon before REVIEW-1.
        with self.assertRaises(TypeError) as ctx:
            quick_request(forecast=0.9)
        self.assertIn("forecast", str(ctx.exception))

    def test_fractional_backcast_refused(self):
        with self.assertRaises(TypeError) as ctx:
            quick_request(backcast=0.9)
        self.assertIn("backcast", str(ctx.exception))

    def test_nan_backcast_refused(self):
        with self.assertRaises(TypeError):
            quick_request(backcast=float("nan"))

    def test_start_year_and_trend_length_exactness(self):
        for kw in ({"start_year": 1970.5}, {"trend_length": 0.9}):
            with self.subTest(**kw):
                with self.assertRaises(TypeError):
                    quick_request(**kw)

    def test_digit_string_frequency_refused(self):
        for bad in ("12", b"12", None):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    quick_request(frequency=bad, seasonal=["msr"] * 12)

    def test_bool_frequency_refused(self):
        # bool passed the old int(frequency) and became frequency=1.
        with self.assertRaises(TypeError):
            quick_request(frequency=True, seasonal=["msr"])

    def test_integral_float_refused_strict_policy(self):
        # Documented strict policy: even an integral float is refused in an
        # integer slot (no silent 12.0 -> 12 coercion at the boundary).
        with self.assertRaises(TypeError):
            quick_request(frequency=12.0, seasonal=["msr"] * 12)

    @unittest.skipUnless(HAS_NUMPY, "numpy not installed")
    def test_numpy_integer_scalars_accepted(self):
        # The documented accepted interop set: numpy integer scalars pass
        # and the request reaches the CORE (quarterly -> core status, the
        # cheap pre-fit refusal), proving no boundary TypeError.
        result = quick_request(frequency=np.int64(4), start_period=np.int64(1),
                               backcast=np.int64(0), forecast=np.int64(2),
                               seasonal=["msr"] * 4)
        self.assertEqual(result["status"], MONTHLY_ONLY)
        self.assertFalse(result["available"])


class FlagTest(unittest.TestCase):
    """Flags are decision inputs: real bools only, truthiness never counts."""

    FLAGS = ("outliers", "use_calendar_detection", "use_easter_detection",
             "automatic_trading_days", "use_user_variables")

    def test_text_and_number_flags_refused(self):
        for flag in self.FLAGS:
            for bad in ("False", 1, 0, "true"):
                with self.subTest(flag=flag, bad=bad):
                    with self.assertRaises(TypeError) as ctx:
                        quick_request(**{flag: bad})
                    self.assertIn(flag, str(ctx.exception))

    @unittest.skipUnless(HAS_NUMPY, "numpy not installed")
    def test_numpy_bool_accepted(self):
        # numpy bool_ is the documented accepted scalar: np.bool_(True) on a
        # deferred flag reaches the CORE's deferred status (boundary passed).
        for flag in ("use_calendar_detection", "use_easter_detection",
                     "automatic_trading_days", "use_user_variables"):
            with self.subTest(flag=flag):
                result = quick_request(**{flag: np.bool_(True)})
                self.assertEqual(result["status"], DEFERRED)


class OutlierSpanTest(unittest.TestCase):
    """Exactly two integer endpoints; a third value is never silently dropped."""

    def test_three_endpoint_span_refused(self):
        with self.assertRaises(TypeError) as ctx:
            quick_request(outliers=True, outlier_span=(0, 5, 9))
        self.assertIn("two integer endpoints", str(ctx.exception))

    def test_single_endpoint_span_refused(self):
        with self.assertRaises(TypeError):
            quick_request(outliers=True, outlier_span=(1,))

    def test_fractional_span_refused(self):
        # (0.9, 5.9) used to become (0, 5) — moved and truncated silently.
        with self.assertRaises(TypeError) as ctx:
            quick_request(outliers=True, outlier_span=(0.9, 5.9))
        self.assertIn("outlier_span", str(ctx.exception))

    def test_digit_string_span_refused(self):
        # "12" used to become the span (1, 2) through string indexing.
        with self.assertRaises(TypeError) as ctx:
            quick_request(outliers=True, outlier_span="12")
        self.assertIn("outlier_span", str(ctx.exception))

    def test_valid_narrow_span_still_gets_core_status(self):
        # Well-formed: the boundary must NOT pre-empt the core's verbatim
        # full-span-only refusal.
        result = quick_request(outliers=True, outlier_span=(10, 80))
        self.assertEqual(result["status"], SPAN_ONLY)

    @unittest.skipUnless(HAS_NUMPY, "numpy not installed")
    def test_numpy_integer_span_accepted(self):
        result = quick_request(outliers=True,
                               outlier_span=(np.int64(10), np.int64(80)))
        self.assertEqual(result["status"], SPAN_ONLY)


class SeriesTest(unittest.TestCase):
    """The digit-string/bytes-to-core bug: text/binary/matrix refused."""

    def test_digit_string_series_refused(self):
        # The review: "both a digit string and bytes reached the core as
        # series input" — now a naming boundary TypeError.
        with self.assertRaises(TypeError) as ctx:
            pykalos.x13_automatic("1234567890" * 12)
        self.assertIn("digit string", str(ctx.exception))

    def test_bytes_series_refused(self):
        with self.assertRaises(TypeError):
            pykalos.x13_automatic(b"\x01\x02" * 60)

    def test_string_elements_refused_not_parsed(self):
        # ["1.5", ...] used to float() into a series.
        with self.assertRaises(TypeError) as ctx:
            pykalos.x13_automatic(["1.5"] * 120)
        self.assertIn("element 0", str(ctx.exception))

    def test_multivariate_list_refused(self):
        with self.assertRaises(TypeError) as ctx:
            pykalos.x13_automatic([[1.0, 2.0]] * 60)
        self.assertIn("multivariate", str(ctx.exception))

    def test_dict_series_refused(self):
        # Iterating a mapping's keys is never a series.
        with self.assertRaises(TypeError) as ctx:
            pykalos.x13_automatic({i: float(i) for i in range(120)})
        self.assertIn("mapping", str(ctx.exception))

    def test_ordered_iterables_still_accepted(self):
        # The supported numeric-iterable set is preserved (tuple, generator)
        # — proven cheaply through the quarterly pre-fit core refusal.
        values = list(QUICK["values"])
        kw = dict(start_year=QUICK["first_year"], start_period=QUICK["first_period"],
                  frequency=4, seasonal=["msr"] * 4)
        self.assertEqual(pykalos.x13_automatic(tuple(values), **kw)["status"],
                         MONTHLY_ONLY)
        self.assertEqual(pykalos.x13_automatic(iter(values), **kw)["status"],
                         MONTHLY_ONLY)

    def test_nan_element_keeps_core_finite_status(self):
        broken = list(QUICK["values"])
        broken[5] = float("nan")
        result = pykalos.x13_automatic(broken, start_year=QUICK["first_year"],
                                       start_period=QUICK["first_period"])
        self.assertEqual(result["status"], FINITE)
        self.assertFalse(result["available"])

    @unittest.skipUnless(HAS_NUMPY, "numpy not installed")
    def test_multivariate_ndarray_refused(self):
        with self.assertRaises(TypeError) as ctx:
            pykalos.x13_automatic(np.arange(240.0).reshape(2, 120))
        self.assertIn("ndim=2", str(ctx.exception))

    @unittest.skipUnless(HAS_NUMPY, "numpy not installed")
    def test_numpy_scalar_series_refused(self):
        with self.assertRaises(TypeError):
            pykalos.x13_automatic(np.float64(3.0))

    @unittest.skipUnless(HAS_NUMPY, "numpy not installed")
    def test_integer_ndarray_and_readonly_view_accepted(self):
        # Preserved supported inputs: int64 ndarray and a read-only 1-D
        # float64 view both still reach the core (quarterly keeps it cheap).
        arr = np.arange(2 * len(QUICK["values"]), dtype=np.int64)
        self.assertEqual(pykalos.x13_automatic(
            arr, start_year=1990, start_period=1, frequency=4,
            seasonal=["msr"] * 4)["status"], MONTHLY_ONLY)
        ro = np.asarray(QUICK["values"], dtype=np.float64)
        ro.setflags(write=False)
        self.assertEqual(pykalos.x13_automatic(
            ro, start_year=QUICK["first_year"],
            start_period=QUICK["first_period"],
            frequency=4, seasonal=["msr"] * 4)["status"], MONTHLY_ONLY)


def _raw_request(**over):
    request = dict(pykalos._X13_AUTOMATIC_DEFAULTS)
    request.update({
        "input": list(QUICK["values"]), "frequency": 12,
        "first_year": QUICK["first_year"], "first_period": QUICK["first_period"],
        "outliers_used": False, "outlier_types": [0, 1, 2, 3],
        "outlier_span": None, "seasonal": ["msr"] * 12, "trend_length": 0,
        "sigma": "legacy", "lower_sigma": 1.5, "upper_sigma": 2.5,
        "msr_policy": "jdplus", "mode": "undefined", "backcast": 0, "forecast": 0,
    })
    request.update(over)
    return request


class RawBoundaryTest(unittest.TestCase):
    """The raw x13_automatic_fit entry: schema keys, budgets, strict flags."""

    def test_valid_raw_request_unchanged(self):
        # The valid row through the raw entry: same contract, same status.
        # (The raw entry returns the core result verbatim: the "available"
        # provenance key is the product wrapper's, not the raw entry's.)
        result = pykalos.x13_automatic_fit(_raw_request())
        self.assertEqual(result["status"], "available")

    def test_typo_key_raises_naming_it(self):
        with self.assertRaises(TypeError) as ctx:
            pykalos.x13_automatic_fit(_raw_request(use_calender_detection=True))
        self.assertIn("use_calender_detection", str(ctx.exception))

    def test_multiple_unknown_keys_all_named(self):
        with self.assertRaises(TypeError) as ctx:
            pykalos.x13_automatic_fit(_raw_request(foo=1,baar=False))
        msg = str(ctx.exception)
        self.assertIn("baar", msg)
        self.assertIn("foo", msg)

    def test_negative_round_budget_refused(self):
        with self.assertRaises(ValueError) as ctx:
            pykalos.x13_automatic_fit(_raw_request(outlier_max_round=-1))
        self.assertIn("outlier_max_round", str(ctx.exception))
        self.assertIn("-1", str(ctx.exception))

    def test_negative_outlier_budget_refused(self):
        with self.assertRaises(ValueError) as ctx:
            pykalos.x13_automatic_fit(_raw_request(outlier_max_outliers=-2))
        self.assertIn("outlier_max_outliers", str(ctx.exception))
        self.assertIn("-2", str(ctx.exception))

    def test_negative_budgets_refused_through_convenience_entry(self):
        # **overrides ride straight to the raw parser: same ValueError.
        for kw, name in (({"outlier_max_round": -1}, "outlier_max_round"),
                         ({"outlier_max_outliers": -3}, "outlier_max_outliers")):
            with self.subTest(**kw):
                with self.assertRaises(ValueError) as ctx:
                    quick_request(**kw)
                self.assertIn(name, str(ctx.exception))

    def test_typo_override_refused_through_convenience_entry(self):
        with self.assertRaises(TypeError) as ctx:
            quick_request(use_calender_detection=True)
        self.assertIn("use_calender_detection", str(ctx.exception))

    def test_positive_budgets_accepted_both_entries(self):
        # The valid row: explicit nonnegative budgets ride through unchanged.
        result = pykalos.x13_automatic_fit(
            _raw_request(outlier_max_round=0, outlier_max_outliers=0))
        self.assertEqual(result["status"], "available")

    def test_string_and_number_flags_refused_raw(self):
        for bad in ("False", 1, 0.0):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError) as ctx:
                    pykalos.x13_automatic_fit(_raw_request(use_calendar_detection=bad))
                self.assertIn("use_calendar_detection", str(ctx.exception))

    @unittest.skipUnless(HAS_NUMPY, "numpy not installed")
    def test_numpy_bool_refused_at_raw_entry_documented(self):
        # Documented asymmetry: numpy bool_ is a product-entry convenience;
        # the RAW entry takes real Python bools only.
        with self.assertRaises(TypeError):
            pykalos.x13_automatic_fit(_raw_request(use_calendar_detection=np.bool_(True)))

    def test_digit_string_and_bytes_input_refused_raw(self):
        for bad in ("1234567890" * 12, b"\x01\x02" * 60,
                    memoryview(b"\x01\x02" * 60)):
            with self.subTest(kind=type(bad).__name__):
                with self.assertRaises(TypeError) as ctx:
                    pykalos.x13_automatic_fit(_raw_request(input=bad))
                self.assertIn("'input'", str(ctx.exception))

    def test_mapping_and_set_input_refused_raw(self):
        # The old caster refused these; the explicit iterable policy keeps
        # them refused (mapping keys / unordered sets are never a series).
        with self.assertRaises(TypeError) as ctx:
            pykalos.x13_automatic_fit(_raw_request(input={i: 1.0 for i in range(60)}))
        self.assertIn("'input'", str(ctx.exception))
        with self.assertRaises(TypeError):
            pykalos.x13_automatic_fit(_raw_request(input=set(range(60))))

    def test_list_of_strings_input_refused_raw(self):
        # The per-element PyFloat path used to parse ["101.0", ...].
        with self.assertRaises(TypeError) as ctx:
            pykalos.x13_automatic_fit(_raw_request(input=["101.0"] * len(QUICK["values"])))
        self.assertIn("text elements are refused", str(ctx.exception))

    @unittest.skipUnless(HAS_NUMPY, "numpy not installed")
    def test_multivariate_input_refused_raw(self):
        with self.assertRaises(TypeError) as ctx:
            pykalos.x13_automatic_fit(_raw_request(input=np.arange(240.0).reshape(2, 120)))
        self.assertIn("non-scalar", str(ctx.exception))

    @unittest.skipUnless(HAS_NUMPY, "numpy not installed")
    def test_numpy_array_and_int_input_still_accepted_raw(self):
        # Preserved raw support: float64 and int64 1-D arrays (cheap core
        # refusal keeps this fast).
        base = _raw_request(frequency=4, seasonal=["msr"] * 4)
        base["input"] = np.asarray(QUICK["values"])
        self.assertEqual(pykalos.x13_automatic_fit(base)["status"], MONTHLY_ONLY)
        base["input"] = np.arange(len(QUICK["values"]), dtype=np.int64) + 100
        self.assertEqual(pykalos.x13_automatic_fit(base)["status"], MONTHLY_ONLY)

    def test_float_and_bool_integers_refused_raw(self):
        for kw in ({"frequency": 12.9}, {"frequency": True}, {"forecast": 0.9},
                   {"max_d": 2.0}, {"trend_length": "0"}):
            with self.subTest(**kw):
                key = next(iter(kw))
                with self.assertRaises(TypeError) as ctx:
                    pykalos.x13_automatic_fit(_raw_request(**kw))
                self.assertIn(f"'{key}'", str(ctx.exception))

    @unittest.skipUnless(HAS_NUMPY, "numpy not installed")
    def test_numpy_integer_scalars_accepted_raw(self):
        base = _raw_request(frequency=np.int64(4), seasonal=["msr"] * 4,
                            backcast=np.int64(0), forecast=np.int64(2),
                            outlier_max_round=np.int64(30),
                            outlier_max_outliers=np.int64(30))
        self.assertEqual(pykalos.x13_automatic_fit(base)["status"], MONTHLY_ONLY)

    def test_span_endpoints_checked_raw(self):
        for bad in ((0, 5, 9), (0.9, 5.9), "12", (1,), (True, 5)):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError) as ctx:
                    pykalos.x13_automatic_fit(
                        _raw_request(outliers_used=True, outlier_span=bad))
                self.assertIn("outlier_span", str(ctx.exception))

    def test_missing_field_message_unchanged(self):
        request = _raw_request()
        del request["mode"]
        with self.assertRaises(KeyError) as ctx:
            pykalos.x13_automatic_fit(request)
        self.assertIn("missing field", str(ctx.exception))

    def test_explicit_sigma_contract_unchanged(self):
        # REVIEW-1 keeps the raw entry's explicit-sigma contract verbatim.
        request = _raw_request()
        del request["sigma"]
        self.assertEqual(
            pykalos.x13_automatic_fit(request)["status"],
            "unsupported:x13 fit requires an explicit sigma policy")


class CoreStatusPinnedTest(unittest.TestCase):
    """Valid rows pin the EXISTING core statuses, unchanged by REVIEW-1."""

    def test_monthly_valid_request_available(self):
        result = quick_request()
        self.assertEqual(result["status"], "available")
        self.assertTrue(result["available"])
        self.assertEqual(result["sigma_policy_provenance"], "legacy (default)")

    def test_quarterly_valid_request_keeps_core_status(self):
        # frequency=4 is WELL-FORMED but unsupported: it must reach the
        # core and keep the verbatim status (never a boundary TypeError).
        result = quick_request(frequency=4, seasonal=["msr"] * 4)
        self.assertEqual(result["status"], MONTHLY_ONLY)
        self.assertFalse(result["available"])

    def test_deferred_detection_flags_keep_core_status(self):
        for flag in ("use_calendar_detection", "use_easter_detection",
                     "automatic_trading_days", "use_user_variables"):
            with self.subTest(flag=flag):
                result = quick_request(**{flag: True})
                self.assertEqual(result["status"], DEFERRED)

    def test_fractional_frequency_never_reaches_core(self):
        # The contrast pair: 4 (well-formed, unsupported) reaches the core,
        # 4.9 (malformed) is a boundary TypeError — and the seasonal default
        # is never allocated from a to-be-refused frequency.
        with self.assertRaises(TypeError):
            quick_request(frequency=4.9)


if __name__ == "__main__":
    unittest.main()
