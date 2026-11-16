"""NumPy interoperability qualification at the minimal convolve surface (M2).

Documents and pins the boundary semantics proven by the M2 acceptance study
(see IMPLEMENTATION_STATUS.md): copy-in of any 1-D numeric vector, including
float64 arrays, strided/negative-stride views and read-only buffers; strict
rejection of non-vector inputs; NaN/Inf/empty handled by core policy.
"""
import importlib.util
import math
import time
import unittest
import warnings

import pykalos

HAS_NUMPY = importlib.util.find_spec("numpy") is not None

if HAS_NUMPY:
    import numpy as np

LEFT = [1.0, -0.4]
RIGHT = [1.0, 0.2]
PRODUCT = [1.0, -0.2, -0.08000000000000002]


@unittest.skipUnless(HAS_NUMPY, "numpy not installed")
class NumPyInteropTest(unittest.TestCase):
    def test_float64_arrays_match_lists(self):
        out = pykalos.convolve(np.array(LEFT), np.array(RIGHT))
        self.assertIsInstance(out, list)
        self.assertEqual(out, PRODUCT)

    def test_noncontiguous_views(self):
        base = np.array([1.0, 9.0, -0.4, 9.0])
        self.assertEqual(pykalos.convolve(base[::2], np.array(RIGHT)), PRODUCT)
        self.assertEqual(pykalos.convolve(np.array([-0.4, 1.0])[::-1], np.array(RIGHT)), PRODUCT)
        self.assertEqual(pykalos.convolve(np.array([[9.0, 1.0, -0.4, 9.0]])[0][1:3], np.array(RIGHT)), PRODUCT)

    def test_readonly_buffers_accepted(self):
        ro = np.array(LEFT)
        ro.setflags(write=False)
        self.assertEqual(pykalos.convolve(ro, np.array(RIGHT)), PRODUCT)
        frozen = memoryview(np.frombuffer(np.array(LEFT, dtype=np.float64).tobytes()))
        self.assertTrue(frozen.readonly)
        self.assertEqual(pykalos.convolve(frozen, RIGHT), PRODUCT)

    def test_other_dtypes_and_iterables_converted_per_element(self):
        self.assertEqual(pykalos.convolve(np.array([1, -4], dtype=np.int64), np.array([10])), [10.0, -40.0])
        f32_out = pykalos.convolve(np.array(LEFT, dtype=np.float32), np.array(RIGHT, dtype=np.float32))
        for got, want in zip(f32_out, PRODUCT):
            self.assertAlmostEqual(got, want, delta=1e-7)  # per-element f32 conversion, so not bit-exact
        self.assertEqual(pykalos.convolve((x for x in LEFT), tuple(RIGHT)), PRODUCT)
        self.assertEqual(pykalos.convolve(np.array([True, False]), np.array([2.0])), [2.0, 0.0])

    def test_non_vector_inputs_rejected(self):
        for bad in (np.array([LEFT]), np.array([LEFT]).T, np.float64(1.0), b"\x00" * 16, "12"):
            with self.assertRaises(TypeError):
                pykalos.convolve(bad, RIGHT)

    def test_nan_inf_and_empty_follow_core_policy(self):
        for bad in (np.array([1.0, np.nan]), np.array([1.0, np.inf]), np.array([])):
            with self.assertRaises(ValueError):
                pykalos.convolve(bad, RIGHT)
        # The core's message, not a binding-side reinterpretation, is what callers see.
        with self.assertRaises(ValueError) as ctx:
            pykalos.convolve(np.array([np.nan]), np.array([1.0]))
        self.assertIn("finite", str(ctx.exception))

    def test_masked_arrays_rejected_via_nan_policy(self):
        masked = np.ma.masked_array(LEFT, mask=[False, True])
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)  # numpy: masked element -> nan
            with self.assertRaises(ValueError):
                pykalos.convolve(masked, RIGHT)

    def test_inputs_are_copied_in_not_aliased(self):
        arr = np.array(LEFT)
        out = pykalos.convolve(arr, np.array(RIGHT))
        arr[1] = 99.0
        self.assertEqual(out, PRODUCT)  # result was computed from the copy
        self.assertEqual(pykalos.convolve(arr, np.array(RIGHT)), [1.0, 99.2, 19.8])

    def test_large_array_timing_sanity(self):
        big = np.ones(1_000_000, dtype=np.float64)
        start = time.monotonic()
        out = pykalos.convolve(big, [1.0])
        elapsed = time.monotonic() - start
        self.assertEqual(len(out), 1_000_000)
        self.assertTrue(all(math.isfinite(v) for v in (out[0], out[-1])))
        self.assertLess(elapsed, 20.0, "1M-element copy-in + single-tap convolution should be fast")
        start = time.monotonic()
        out = pykalos.convolve(big[::2], [1.0, -0.5, 0.25])
        elapsed = time.monotonic() - start
        self.assertEqual(len(out), 500_002)
        self.assertLess(elapsed, 20.0, "strided 500k view path should be fast")


if __name__ == "__main__":
    unittest.main()
