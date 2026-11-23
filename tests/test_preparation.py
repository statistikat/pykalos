import math
import unittest

import pykalos


class Preparation(unittest.TestCase):
    def test_generated_columns_follow_source_origin(self):
        for frequency in (4, 12):
            start = (-1, frequency)
            x = list(range(10 * frequency))
            x[0] = float("nan")  # Outside the required regressor span.
            spec = dict(length=6 * frequency, start=start, frequency=frequency,
                        estimation_start=(0, 2), estimation_end=(1, frequency),
                        regressors=[dict(name="x", start=(-2, 1), values=x)], forecast=3, backcast=2)
            for d in range(3):
                for sd in range(3):
                    if not (d or sd):
                        continue
                    with self.subTest(frequency=frequency, d=d, seasonal_d=sd):
                        prepared = pykalos.prepare_regression(**spec, d=d, seasonal_d=sd, include_drift=True,
                            coefficients=[dict(name="x", value=2, fixed=True)])
                        n = 2*frequency - 1
                        self.assertEqual(prepared["observed"], dict(start=(0, 2), frequency=frequency, length=n))
                        self.assertEqual(prepared["required"], dict(start=start, frequency=frequency, length=n+5))
                        self.assertEqual((prepared["observed_offset"], prepared["source_offset"]), (2, 2))
                        self.assertEqual(prepared["names"], ["x", "drift"])
                        self.assertEqual(prepared["generated"], ["drift"])
                        self.assertEqual(prepared["design"]["fixed"], [True, False])
                        self.assertEqual(prepared["design"]["coefficients"], [2., 0.])
                        for col, full in zip(prepared["design"]["columns"], prepared["columns"]):
                            self.assertEqual(col, full[2:-3])
                        for i, v in enumerate(prepared["design"]["columns"][1]):
                            expected = (i + 3)**(d + sd) / (math.factorial(d+sd) * frequency**sd)
                            self.assertAlmostEqual(v, expected, delta=1e-12 * max(1, expected))
            mean = pykalos.prepare_regression(**spec, include_mean=True)
            self.assertEqual(mean["generated"], ["mean"])
            self.assertEqual(mean["columns"][1], [1.]*(2*frequency+4))

    def test_transform_and_jacobian(self):
        data = [0., math.e, 0., math.exp(3.), math.exp(4.)]
        mask = [True, False, True, False, False]
        log = pykalos.prepare_series(data, transformation="log", degree=2, missing=mask, source_offset=10)
        self.assertEqual(log["missing"], mask)
        self.assertEqual(log["local_rows"], [3, 4])
        self.assertEqual(log["source_rows"], [13, 14])
        self.assertEqual(log["log_jacobian_terms"], [0.,0.,0.,-3.,-4.])
        self.assertEqual(log["log_jacobian"], -7.)
        plain = pykalos.prepare_series(data, transformation="none", degree=2, missing=mask)
        self.assertEqual(plain["local_rows"], [1, 3, 4])
        self.assertEqual(plain["values"], data)
        self.assertEqual(plain["log_jacobian"], 0.)

    def test_refusals(self):
        base = dict(length=12, start=(1999, 1), frequency=12)
        for arg in (dict(backcast=-1), dict(estimation_end=(2002, 1)), dict(d=1, include_mean=True),
                    dict(d=True), dict(start=(2000, 1.)), dict(regressors=[{}])):
            with self.subTest(arg=arg), self.assertRaises((ValueError, TypeError)):
                pykalos.prepare_regression(**(base | arg))
        with self.assertRaises((TypeError,ValueError)):
            pykalos.prepare_series([3, 2], transformation="log", degree=0, missing=[1,0])
        with self.assertRaises(ValueError):
            pykalos.prepare_series([3,-2], transformation="log", degree=0)
